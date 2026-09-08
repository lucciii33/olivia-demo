# Sailtrim Demo — API + MCP

Demo standalone (Python + SQLite) para probar y presentar. Módulo de
**Inventario & Órdenes** inspirado en tu app `sailtrimbackend`.

Todo vive en una sola carpeta para desplegar fácil. Nada del proyecto
original fue modificado.

## Qué incluye

- **`app.py`** — API REST con **15 endpoints** (FastAPI).
- **`mcp_server.py`** — servidor **MCP con 7 tools** que consumen la API.
- **`db.py`** — SQLite: esquema + datos de demo (se autogenera al arrancar).
- **`auth.py`** — protección con **API key O Bearer token** (basta con uno).

## Correr (VS Code / terminal)

```bash
cd sailtrim-demo
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 1) API  ->  http://localhost:8000  (docs: /docs)
python app.py

# 2) MCP (en otra terminal, con el venv activo)
python mcp_server.py
```

La DB `demo.db` se crea sola con productos y órdenes de ejemplo.

## Autenticación (una u otra, no las dos)

Todos los endpoints menos `GET /health` requieren **una** de estas:

- Header API key:  `X-API-Key: demo-api-key-123`
- Bearer token:    `Authorization: Bearer demo-bearer-token-abc`

Cámbialas en un archivo `.env` (ver `.env.example`) antes de desplegar:
`API_KEY`, `BEARER_TOKEN`.

```bash
# ejemplos
curl localhost:8000/health
curl localhost:8000/products -H "X-API-Key: demo-api-key-123"
curl localhost:8000/stats/overview -H "Authorization: Bearer demo-bearer-token-abc"
```

## Los 15 endpoints

| #  | Método | Ruta                                  | Qué hace |
|----|--------|---------------------------------------|----------|
| 1  | GET    | `/health`                             | Health check (público) |
| 2  | POST   | `/products`                           | Crear producto |
| 3  | GET    | `/products`                           | Listar / buscar productos |
| 4  | GET    | `/products/low-stock`                 | Productos con stock bajo |
| 5  | GET    | `/products/{id}`                      | Ver un producto |
| 6  | PUT    | `/products/{id}`                      | Actualizar producto |
| 7  | DELETE | `/products/{id}`                      | Eliminar producto |
| 8  | POST   | `/products/{id}/adjust-stock`         | Ajustar stock (+/-) |
| 9  | POST   | `/orders`                             | Crear orden (descuenta stock) |
| 10 | GET    | `/orders`                             | Listar órdenes |
| 11 | GET    | `/orders/{id}`                        | Ver orden con ítems |
| 12 | PATCH  | `/orders/{id}/status`                 | Cambiar estado (cancelar repone stock) |
| 13 | GET    | `/customers`                          | Clientes (derivados de órdenes) |
| 14 | GET    | `/stats/overview`                     | Métricas: inventario, ventas, stock bajo |
| 15 | GET    | `/stats/top-products`                 | Productos más vendidos |

## Las 7 MCP tools

1. `list_products` — listar/buscar productos
2. `get_product` — detalle de un producto
3. `check_low_stock` — alertas de reposición
4. `adjust_stock` — ajustar inventario
5. `create_order` — crear orden y descontar stock
6. `set_order_status` — cambiar estado de una orden
7. `business_dashboard` — resumen de negocio + top ventas

### Conectar el MCP a Claude Desktop / VS Code

```json
{
  "mcpServers": {
    "sailtrim-demo": {
      "command": "python",
      "args": ["/ruta/absoluta/sailtrim-demo/mcp_server.py"],
      "env": { "API_BASE": "http://localhost:8000", "API_KEY": "demo-api-key-123" }
    }
  }
}
```
