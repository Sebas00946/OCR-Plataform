"""
Clasificador TF-IDF para facturas.

Aprende de las clasificaciones históricas (trazabilidad_facturas + ocr_clasificacion_historial)
y predice la UF correcta para facturas nuevas.

Características:
- Se entrena con datos existentes al arrancar
- Aprendizaje incremental con partial_fit() en cada validación
- Combina con reglas: si la regla y TF-IDF coinciden → confianza máxima
- Si no coinciden → registra conflicto para revisión
- Registra por qué falló (para aprender de errores)
"""

import os
import pickle
import logging
from typing import Dict, Optional, Tuple, List
from datetime import datetime

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import SGDClassifier
    from sklearn.calibration import CalibratedClassifierCV
    import numpy as np
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

from .database import db

logger = logging.getLogger('OCR_API')

MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'tfidf_model.pkl')


class TFIDFClassifier:
    """Clasificador de facturas basado en TF-IDF + SGD con aprendizaje incremental."""

    def __init__(self):
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.classifier: Optional[SGDClassifier] = None
        self.classes: List[int] = []
        self.uf_names: Dict[int, str] = {}
        self.trained = False
        self.train_count = 0
        self.last_train = None

    def train_from_db(self, limit: int = 5000) -> Dict:
        """
        Entrena el modelo con datos de la BD.
        Usa trazabilidad_facturas + ocr_clasificacion_historial.
        """
        if not HAS_SKLEARN:
            return {'success': False, 'error': 'scikit-learn no instalado'}

        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()

                # Obtener textos y etiquetas de ocr_clasificacion_historial
                # que tengan datos_extraidos (contiene el texto del XML/PDF)
                cursor.execute("""
                    SELECT 
                        h.datos_extraidos,
                        h.unidad_funcional_detectada_id as uf_id,
                        uf.nombre as uf_nombre
                    FROM ocr_clasificacion_historial h
                    JOIN unidades_funcionales uf ON uf.id = h.unidad_funcional_detectada_id
                    WHERE h.unidad_funcional_detectada_id IS NOT NULL
                        AND h.datos_extraidos IS NOT NULL
                    ORDER BY h.id DESC
                    LIMIT %s
                """, (limit,))

                rows = cursor.fetchall()
                cursor.close()

            if len(rows) < 50:
                return {'success': False, 'error': f'Datos insuficientes: {len(rows)} (mínimo 50)'}

            textos = []
            etiquetas = []

            for row in rows:
                datos = row[0]  # jsonb datos_extraidos
                uf_id = row[1]
                uf_nombre = row[2]

                # Extraer texto del campo datos_extraidos
                texto = self._extraer_texto_de_datos(datos)
                if texto and len(texto) > 20:
                    textos.append(texto)
                    etiquetas.append(uf_id)
                    self.uf_names[uf_id] = uf_nombre

            if len(textos) < 50:
                return {'success': False, 'error': f'Textos válidos insuficientes: {len(textos)}'}

            # Entrenar TF-IDF Vectorizer
            self.vectorizer = TfidfVectorizer(
                max_features=3000,
                ngram_range=(1, 2),  # Unigrams + bigrams
                min_df=2,
                max_df=0.95,
                strip_accents='unicode',
                lowercase=True,
                sublinear_tf=True
            )

            X = self.vectorizer.fit_transform(textos)

            # Entrenar clasificador SGD (soporta partial_fit para incremental)
            self.classes = sorted(list(set(etiquetas)))
            self.classifier = SGDClassifier(
                loss='modified_huber',  # Permite predict_proba
                penalty='l2',
                alpha=1e-4,
                max_iter=100,
                random_state=42,
                class_weight='balanced'
            )
            self.classifier.fit(X, etiquetas)

            self.trained = True
            self.train_count = len(textos)
            self.last_train = datetime.now().isoformat()

            # Guardar modelo
            self._save_model()

            logger.info(f"TF-IDF entrenado: {len(textos)} documentos, {len(self.classes)} UFs")

            return {
                'success': True,
                'documentos': len(textos),
                'unidades_funcionales': len(self.classes),
                'features': self.vectorizer.max_features
            }

        except Exception as e:
            logger.warning(f"Error entrenando TF-IDF: {e}")
            return {'success': False, 'error': str(e)}

    def predict(self, texto: str, nit: str = '', regla_uf_id: int = None) -> Dict:
        """
        Predice la UF para un texto de factura.

        Args:
            texto: Texto extraído del XML/PDF
            nit: NIT del proveedor (se agrega al texto para contexto)
            regla_uf_id: UF sugerida por la regla (si existe)

        Returns:
            Dict con predicción, confianza, y si coincide con la regla
        """
        if not self.trained or not self.vectorizer or not self.classifier:
            return {'success': False, 'reason': 'Modelo no entrenado'}

        if not texto or len(texto) < 10:
            return {'success': False, 'reason': 'Texto insuficiente'}

        try:
            # Agregar NIT al texto para dar contexto de proveedor
            texto_completo = f"{nit} {texto}" if nit else texto

            X = self.vectorizer.transform([texto_completo.upper()])

            # Predicción
            uf_predicha = self.classifier.predict(X)[0]

            # Probabilidades (confianza)
            probas = self.classifier.predict_proba(X)[0] if hasattr(self.classifier, 'predict_proba') else None

            confidence = 0.0
            top3 = []
            if probas is not None:
                # Top 3 predicciones
                indices = np.argsort(probas)[::-1][:3]
                for idx in indices:
                    uf_id = self.classifier.classes_[idx]
                    prob = probas[idx]
                    top3.append({
                        'uf_id': int(uf_id),
                        'uf_nombre': self.uf_names.get(int(uf_id), f'UF-{uf_id}'),
                        'probabilidad': round(float(prob), 4)
                    })
                confidence = float(probas[indices[0]])

            # Verificar coincidencia con regla
            coincide_con_regla = None
            if regla_uf_id is not None:
                coincide_con_regla = (int(uf_predicha) == regla_uf_id)
                if coincide_con_regla:
                    confidence = min(confidence + 0.2, 1.0)  # Boost si coinciden

            return {
                'success': True,
                'uf_id': int(uf_predicha),
                'uf_nombre': self.uf_names.get(int(uf_predicha), f'UF-{uf_predicha}'),
                'confidence': round(confidence, 4),
                'coincide_con_regla': coincide_con_regla,
                'top3': top3,
                'model_info': {
                    'train_count': self.train_count,
                    'last_train': self.last_train
                }
            }

        except Exception as e:
            return {'success': False, 'reason': str(e)}

    def learn(self, texto: str, uf_correcta_id: int, nit: str = ''):
        """
        Aprendizaje incremental: actualiza el modelo con una nueva muestra.
        Se llama cada vez que una factura es validada/reclasificada.
        """
        if not self.trained or not self.vectorizer:
            return

        try:
            texto_completo = f"{nit} {texto}" if nit else texto
            X = self.vectorizer.transform([texto_completo.upper()])

            # partial_fit actualiza el modelo sin reentrenar todo
            self.classifier.partial_fit(X, [uf_correcta_id])
            self.train_count += 1

            # Actualizar nombre si no lo tiene
            if uf_correcta_id not in self.uf_names:
                try:
                    with db.get_connection() as conn:
                        cur = conn.cursor()
                        cur.execute("SELECT nombre FROM unidades_funcionales WHERE id = %s", (uf_correcta_id,))
                        row = cur.fetchone()
                        if row:
                            self.uf_names[uf_correcta_id] = row[0]
                        cur.close()
                except:
                    pass

        except Exception as e:
            logger.warning(f"Error en aprendizaje incremental TF-IDF: {e}")

    def get_stats(self) -> Dict:
        """Retorna estadísticas del modelo."""
        return {
            'trained': self.trained,
            'sklearn_available': HAS_SKLEARN,
            'train_count': self.train_count,
            'last_train': self.last_train,
            'classes': len(self.classes),
            'uf_names': self.uf_names,
            'features': self.vectorizer.max_features if self.vectorizer else 0
        }

    # ============================================
    # MÉTODOS PRIVADOS
    # ============================================

    def _extraer_texto_de_datos(self, datos) -> str:
        """Extrae texto relevante del campo JSONB datos_extraidos."""
        if not datos:
            return ''

        if isinstance(datos, str):
            import json
            try:
                datos = json.loads(datos)
            except:
                return datos

        partes = []

        # Proveedor
        prov = datos.get('proveedor', {}) or {}
        if isinstance(prov, dict):
            partes.append(prov.get('nombre', ''))
            partes.append(prov.get('nit', ''))

        # Factura
        fac = datos.get('factura', {}) or {}
        if isinstance(fac, dict):
            partes.append(fac.get('numero', ''))
            partes.append(fac.get('notas', ''))
            partes.append(fac.get('sucursal_nota', ''))
            partes.append(fac.get('almacen_nota', ''))
            partes.append(fac.get('orden_compra', ''))

        # Cliente
        cli = datos.get('cliente', {}) or {}
        if isinstance(cli, dict):
            partes.append(cli.get('direccion', ''))
            partes.append(cli.get('ciudad', ''))

        # Texto general
        partes.append(datos.get('text', '') or '')

        return ' '.join(p for p in partes if p).upper()

    def _save_model(self):
        """Guarda el modelo en disco."""
        try:
            os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
            with open(MODEL_PATH, 'wb') as f:
                pickle.dump({
                    'vectorizer': self.vectorizer,
                    'classifier': self.classifier,
                    'classes': self.classes,
                    'uf_names': self.uf_names,
                    'train_count': self.train_count,
                    'last_train': self.last_train
                }, f)
        except Exception as e:
            logger.warning(f"Error guardando modelo TF-IDF: {e}")

    def load_model(self) -> bool:
        """Carga modelo desde disco si existe."""
        if not HAS_SKLEARN:
            return False
        try:
            if os.path.exists(MODEL_PATH):
                with open(MODEL_PATH, 'rb') as f:
                    data = pickle.load(f)
                self.vectorizer = data['vectorizer']
                self.classifier = data['classifier']
                self.classes = data['classes']
                self.uf_names = data['uf_names']
                self.train_count = data['train_count']
                self.last_train = data['last_train']
                self.trained = True
                logger.info(f"TF-IDF cargado desde disco: {self.train_count} docs, {len(self.classes)} UFs")
                return True
        except Exception as e:
            logger.warning(f"Error cargando modelo TF-IDF: {e}")
        return False


# Singleton
tfidf_classifier = TFIDFClassifier()
