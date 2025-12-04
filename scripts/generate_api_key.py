"""
Script para generar API keys seguras
"""
import secrets
import string


def generate_api_key(length: int = 32) -> str:
    """
    Generar una API key segura
    
    Args:
        length: Longitud de la key (default: 32)
        
    Returns:
        API key generada
    """
    alphabet = string.ascii_letters + string.digits
    api_key = ''.join(secrets.choice(alphabet) for _ in range(length))
    return api_key


def main():
    """Generar múltiples API keys"""
    print("Generador de API Keys\n")
    print("=" * 50)
    
    num_keys = int(input("¿Cuántas keys deseas generar? (default: 3): ") or "3")
    length = int(input("¿Longitud de cada key? (default: 32): ") or "32")
    
    print(f"\nGenerando {num_keys} API keys de {length} caracteres...\n")
    
    keys = []
    for i in range(num_keys):
        key = generate_api_key(length)
        keys.append(key)
        print(f"Key {i+1}: {key}")
    
    print("\n" + "=" * 50)
    print("\nPara usar estas keys, agrégalas a tu archivo .env:")
    print(f"\nAPI_KEYS={','.join(keys)}")
    print("\n" + "=" * 50)


if __name__ == "__main__":
    main()
