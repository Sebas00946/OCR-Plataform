"""
Sistema Multi-Agente para Clasificación OCR.

Arquitectura de agentes especializados que votan por la mejor clasificación:

1. RuleAgent: Aplica reglas exactas configuradas manualmente
2. ProviderAgent: Usa historial del proveedor específico
3. BayesianAgent: Inferencia probabilística con contexto completo
4. KeywordAgent: Scoring tradicional de keywords
5. FallbackAgent: Heurísticas cuando otros fallan

Cada agente vota con un peso (confidence). El sistema combina votos
usando weighted voting para la decisión final.

Ventajas:
- Robustez: si un agente falla, otros compensan
- Especialización: cada agente es experto en su dominio
- Explicabilidad: se puede ver qué agente influyó más
- Extensibilidad: fácil agregar nuevos agentes
"""
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import Counter

from .engine.knowledge_base import kb
from .engine.fast_classifier import fast_classifier
from .probabilistic_classifier import probabilistic_classifier

logger = logging.getLogger(__name__)


@dataclass
class AgentVote:
    """Voto de un agente para una clasificación."""
    agent_name: str
    unidad_id: Optional[int]
    unidad_nombre: Optional[str]
    confidence: float  # 0.0 - 1.0
    reasoning: str  # Explicación del voto
    metadata: Dict  # Información adicional


class BaseAgent:
    """Clase base para agentes de clasificación."""
    
    def __init__(self, name: str, weight: float = 1.0):
        self.name = name
        self.weight = weight  # Peso del agente en la votación final
    
    def vote(
        self,
        xml_data: Dict,
        pdf_text: str,
        sucursal_id: Optional[int],
        proveedor_id: Optional[int],
        empresa_id: int = 1
    ) -> Optional[AgentVote]:
        """
        Emite un voto para la clasificación.
        Retorna None si el agente no puede votar.
        """
        raise NotImplementedError


class RuleAgent(BaseAgent):
    """Agente que aplica reglas exactas de ocr_reglas_clasificacion."""
    
    def __init__(self):
        super().__init__("RuleAgent", weight=10.0)  # Peso máximo — reglas son definitivas
    
    def vote(self, xml_data, pdf_text, sucursal_id, proveedor_id, empresa_id=1) -> Optional[AgentVote]:
            proveedor = xml_data.get('proveedor', {}) or {}
            nit = ''.join(c for c in str(proveedor.get('nit', '')) if c.isdigit())

            if not nit:
                return None

            # Obtener reglas filtradas por empresa (globales + específicas de esta empresa)
            reglas = kb.get_reglas(empresa_id=empresa_id)
            
            # Filtrar reglas de este NIT
            reglas_nit = []
            for regla in reglas:
                condicion = regla.get('condicion') or {}
                if isinstance(condicion, str):
                    try:
                        condicion = _json.loads(condicion)
                    except Exception:
                        condicion = {}
                
                nit_regla = ''.join(c for c in str(condicion.get('nit', '')) if c.isdigit())
                if nit_regla and nit_regla == nit:
                    reglas_nit.append({**regla, '_condicion': condicion})
            
            if not reglas_nit:
                return None
            
            texto_upper = (pdf_text or '').upper()
            
            # Buscar reglas con sucursal_keyword primero
            for regla in reglas_nit:
                condicion = regla['_condicion']
                keyword = condicion.get('sucursal_keyword', '').strip()
                
                if not keyword:
                    continue
                
                if keyword.upper() in texto_upper:
                    unidad_id = regla.get('unidad_funcional_id')
                    if not unidad_id:
                        continue
                    unidad = kb.get_unidad(unidad_id)
                    if unidad:
                        return AgentVote(
                            agent_name=self.name,
                            unidad_id=unidad['id'],
                            unidad_nombre=unidad['nombre'],
                            confidence=1.0,
                            reasoning=f"Regla NIT+keyword: NIT={nit} keyword='{keyword}' (regla_id={regla.get('id')})",
                            metadata={'regla_id': regla.get('id'), 'keyword': keyword}
                        )
            
            # Reglas simples (sin keyword, sin fallback)
            for regla in reglas_nit:
                condicion = regla['_condicion']
                accion = regla.get('accion') or {}
                if isinstance(accion, str):
                    try:
                        accion = _json.loads(accion)
                    except Exception:
                        accion = {}
                
                if condicion.get('sucursal_keyword'):
                    continue
                if accion.get('es_fallback'):
                    continue
                
                unidad_id = regla.get('unidad_funcional_id')
                if not unidad_id:
                    continue
                unidad = kb.get_unidad(unidad_id)
                if unidad:
                    return AgentVote(
                        agent_name=self.name,
                        unidad_id=unidad['id'],
                        unidad_nombre=unidad['nombre'],
                        confidence=1.0,
                        reasoning=f"Regla exacta ID {regla.get('id')} para NIT {nit}",
                        metadata={'regla_id': regla.get('id')}
                    )
            
            # Fallback
            for regla in reglas_nit:
                accion = regla.get('accion') or {}
                if isinstance(accion, str):
                    try:
                        accion = _json.loads(accion)
                    except Exception:
                        accion = {}
                
                if accion.get('es_fallback'):
                    unidad_id = regla.get('unidad_funcional_id')
                    if not unidad_id:
                        continue
                    unidad = kb.get_unidad(unidad_id)
                    if unidad:
                        return AgentVote(
                            agent_name=self.name,
                            unidad_id=unidad['id'],
                            unidad_nombre=unidad['nombre'],
                            confidence=0.7,
                            reasoning=f"Regla NIT fallback: NIT={nit} (regla_id={regla.get('id')})",
                            metadata={'regla_id': regla.get('id'), 'fallback': True}
                        )
            
            return None



class ProviderAgent(BaseAgent):
    """Agente que usa configuración específica del proveedor."""
    
    def __init__(self):
        super().__init__("ProviderAgent", weight=5.0)
    
    def vote(self, xml_data, pdf_text, sucursal_id, proveedor_id, empresa_id=1) -> Optional[AgentVote]:
        if not proveedor_id:
            proveedor = xml_data.get('proveedor', {}) or {}
            nit = ''.join(c for c in str(proveedor.get('nit', '')) if c.isdigit())
            if nit:
                prov = kb.get_proveedor_by_nit(nit)
                if prov:
                    proveedor_id = prov['id']
        
        if not proveedor_id:
            return None
        
        config = kb.get_proveedor_config(proveedor_id)
        if not config:
            return None
        
        unidades_ids = config.get('unidades_funcionales_ids') or []
        if not unidades_ids:
            return None
        
        # Priorizar unidad de la sucursal detectada
        for uid in unidades_ids:
            if isinstance(uid, dict):
                uid = uid.get('unidad_id') or uid.get('id')
            if not uid:
                continue
            
            unidad = kb.get_unidad(int(uid))
            if unidad:
                # Si coincide con sucursal, alta confianza
                if sucursal_id and unidad['sucursal_id'] == sucursal_id:
                    return AgentVote(
                        agent_name=self.name,
                        unidad_id=unidad['id'],
                        unidad_nombre=unidad['nombre'],
                        confidence=0.9,
                        reasoning=f"Config proveedor + sucursal match",
                        metadata={'proveedor_id': proveedor_id}
                    )
                else:
                    # Sin match de sucursal, confianza media
                    return AgentVote(
                        agent_name=self.name,
                        unidad_id=unidad['id'],
                        unidad_nombre=unidad['nombre'],
                        confidence=0.6,
                        reasoning=f"Config proveedor (sin match sucursal)",
                        metadata={'proveedor_id': proveedor_id}
                    )
        
        return None


class BayesianAgent(BaseAgent):
    """Agente que usa inferencia bayesiana con historial."""
    
    def __init__(self):
        super().__init__("BayesianAgent", weight=4.0)
    
    def vote(self, xml_data, pdf_text, sucursal_id, proveedor_id, empresa_id=1) -> Optional[AgentVote]:
        if not probabilistic_classifier.loaded:
            return None
        
        unidad_id, confidence, debug = probabilistic_classifier.classify(
            xml_data, pdf_text, proveedor_id, sucursal_id
        )
        
        if not unidad_id or confidence < 0.3:
            return None
        
        unidad = kb.get_unidad(unidad_id)
        if not unidad:
            return None
        
        # Construir reasoning desde debug info
        reasoning_parts = []
        if 'proveedor_ciudad' in debug.get(unidad_id, {}):
            reasoning_parts.append("proveedor+ciudad")
        elif 'proveedor' in debug.get(unidad_id, {}):
            reasoning_parts.append("proveedor")
        if 'keywords' in debug.get(unidad_id, {}):
            reasoning_parts.append(f"{len(debug[unidad_id]['keywords'])} keywords")
        
        reasoning = f"Bayesian: {', '.join(reasoning_parts)}" if reasoning_parts else "Bayesian inference"
        
        return AgentVote(
            agent_name=self.name,
            unidad_id=unidad['id'],
            unidad_nombre=unidad['nombre'],
            confidence=confidence,
            reasoning=reasoning,
            metadata=debug.get(unidad_id, {})
        )


class KeywordAgent(BaseAgent):
    """Agente que usa scoring tradicional de keywords."""
    
    def __init__(self):
        super().__init__("KeywordAgent", weight=2.0)
    
    def vote(self, xml_data, pdf_text, sucursal_id, proveedor_id, empresa_id=1) -> Optional[AgentVote]:
        if not pdf_text:
            return None
        
        texto_upper = pdf_text.upper()
        all_keywords = kb.get_all_unidad_keywords()
        
        # Filtrar por sucursal si se especificó
        if sucursal_id:
            unidades_ids = {u['id'] for u in kb.get_unidades_by_sucursal(sucursal_id)}
        else:
            unidades_ids = set(all_keywords.keys())
        
        mejor_score = 0.0
        mejor_unidad_id = None
        mejor_keywords = []
        
        for uid in unidades_ids:
            keywords = all_keywords.get(uid, [])
            if not keywords:
                continue
            
            score = 0.0
            matched = []
            for kw, peso in keywords:
                if kw in texto_upper:
                    score += peso
                    matched.append(kw)
            
            if score > mejor_score:
                mejor_score = score
                mejor_unidad_id = uid
                mejor_keywords = matched
        
        if not mejor_unidad_id or mejor_score < 10:
            return None
        
        unidad = kb.get_unidad(mejor_unidad_id)
        if not unidad:
            return None
        
        # Normalizar score a confidence (0-1)
        confidence = min(mejor_score / 100, 1.0)
        
        return AgentVote(
            agent_name=self.name,
            unidad_id=unidad['id'],
            unidad_nombre=unidad['nombre'],
            confidence=confidence,
            reasoning=f"Keywords: {len(mejor_keywords)} matches, score={mejor_score:.1f}",
            metadata={'keywords': mejor_keywords[:5], 'score': mejor_score}
        )


class FallbackAgent(BaseAgent):
    """Agente de último recurso con heurísticas simples."""
    
    def __init__(self):
        super().__init__("FallbackAgent", weight=0.5)
    
    def vote(self, xml_data, pdf_text, sucursal_id, proveedor_id, empresa_id=1) -> Optional[AgentVote]:
        # Detectar tipo por contenido
        texto_upper = (pdf_text or '').upper()
        proveedor = xml_data.get('proveedor', {}) or {}
        nombre_prov = (proveedor.get('nombre') or proveedor.get('razon_social') or '').upper()
        
        # Keywords de detección rápida
        kw_almacen = ['MEDICAMENTO', 'INSUMO', 'FARMACO', 'DROGUERIA', 'FARMACIA']
        kw_admin = ['SERVICIO', 'MANTENIMIENTO', 'HONORARIO', 'CONSULTORIA']
        
        score_almacen = sum(1 for kw in kw_almacen if kw in texto_upper or kw in nombre_prov)
        score_admin = sum(1 for kw in kw_admin if kw in texto_upper or kw in nombre_prov)
        
        tipo = 'ALMAC' if score_almacen >= score_admin else 'ADMINISTRACI'
        
        # Buscar unidad del tipo en la sucursal
        unidades = kb.get_unidades_by_sucursal(sucursal_id) if sucursal_id else kb.get_all_unidades()
        
        for unidad in unidades:
            if tipo in unidad['nombre'].upper():
                return AgentVote(
                    agent_name=self.name,
                    unidad_id=unidad['id'],
                    unidad_nombre=unidad['nombre'],
                    confidence=0.3,
                    reasoning=f"Fallback: tipo={tipo}",
                    metadata={'tipo': tipo, 'score_almacen': score_almacen, 'score_admin': score_admin}
                )
        
        # Última opción: primera unidad disponible
        if unidades:
            return AgentVote(
                agent_name=self.name,
                unidad_id=unidades[0]['id'],
                unidad_nombre=unidades[0]['nombre'],
                confidence=0.1,
                reasoning="Fallback: primera unidad disponible",
                metadata={}
            )
        
        return None


class MultiAgentClassifier:
    """
    Clasificador que combina votos de múltiples agentes especializados.
    """
    
    def __init__(self):
        self.agents: List[BaseAgent] = [
            RuleAgent(),
            ProviderAgent(),
            BayesianAgent(),
            KeywordAgent(),
            FallbackAgent(),
        ]
        logger.info(f"MultiAgentClassifier inicializado con {len(self.agents)} agentes")
    
    def classify(
        self,
        xml_data: Dict,
        pdf_text: str,
        sucursal_id: Optional[int] = None,
        proveedor_id: Optional[int] = None,
        empresa_id: int = 1
    ) -> Tuple[Dict, List[AgentVote]]:
        """
        Clasifica usando votación de agentes.
        
        Returns:
            (resultado, votos)
        """
        # Recolectar votos de todos los agentes
        votos: List[AgentVote] = []
        
        for agent in self.agents:
            try:
                voto = agent.vote(xml_data, pdf_text, sucursal_id, proveedor_id, empresa_id)
                if voto:
                    votos.append(voto)
                    logger.debug(
                        f"{agent.name} votó: {voto.unidad_nombre} "
                        f"(conf={voto.confidence:.2f}, weight={agent.weight})"
                    )
            except Exception as e:
                logger.error(f"Error en {agent.name}: {e}")
        
        if not votos:
            return {
                'success': False,
                'id': None,
                'nombre': None,
                'confidence': 0.0,
                'method': 'multi_agent_no_votes',
                'votes': []
            }, []
        
        # Si RuleAgent votó, su decisión es final (peso 10.0)
        rule_vote = next((v for v in votos if v.agent_name == 'RuleAgent'), None)
        if rule_vote:
            unidad = kb.get_unidad(rule_vote.unidad_id)
            return {
                'success': True,
                'id': rule_vote.unidad_id,
                'nombre': rule_vote.unidad_nombre,
                'codigo': unidad['codigo'] if unidad else None,
                'sucursal_id': unidad['sucursal_id'] if unidad else None,
                'confidence': 1.0,
                'method': 'multi_agent_rule',
                'votes': [self._vote_to_dict(v) for v in votos]
            }, votos
        
        # Weighted voting: combinar votos con pesos
        weighted_votes = Counter()
        
        for voto in votos:
            agent = next(a for a in self.agents if a.name == voto.agent_name)
            # Peso del agente × confidence del voto
            weighted_votes[voto.unidad_id] += agent.weight * voto.confidence
        
        # Elegir la unidad con mayor peso acumulado
        mejor_unidad_id = weighted_votes.most_common(1)[0][0]
        peso_total = sum(weighted_votes.values())
        confidence_final = weighted_votes[mejor_unidad_id] / peso_total if peso_total > 0 else 0.0
        
        unidad = kb.get_unidad(mejor_unidad_id)
        if not unidad:
            return {
                'success': False,
                'id': None,
                'nombre': None,
                'confidence': 0.0,
                'method': 'multi_agent_error',
                'votes': [self._vote_to_dict(v) for v in votos]
            }, votos
        
        # Determinar qué agentes votaron por la unidad ganadora
        agentes_ganadores = [v.agent_name for v in votos if v.unidad_id == mejor_unidad_id]
        
        return {
            'success': True,
            'id': unidad['id'],
            'nombre': unidad['nombre'],
            'codigo': unidad['codigo'],
            'sucursal_id': unidad['sucursal_id'],
            'confidence': confidence_final,
            'method': f"multi_agent: {', '.join(agentes_ganadores)}",
            'votes': [self._vote_to_dict(v) for v in votos],
            'weighted_scores': dict(weighted_votes)
        }, votos
    
    def _vote_to_dict(self, voto: AgentVote) -> Dict:
        """Convierte AgentVote a dict para JSON."""
        return {
            'agent': voto.agent_name,
            'unidad_id': voto.unidad_id,
            'unidad_nombre': voto.unidad_nombre,
            'confidence': round(voto.confidence, 3),
            'reasoning': voto.reasoning,
            'metadata': voto.metadata
        }


# Instancia global
multi_agent_classifier = MultiAgentClassifier()
