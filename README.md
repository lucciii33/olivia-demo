# Sailtrim Demo — API + MCP

Demo standalone (Python + SQLite) para probar y presentar. Módulo de
**Inventario & Órdenes** inspirado en tu app `sailtrimbackend`.

Todo vive en una sola carpeta para desplegar fácil. Nada del proyecto
original fue modificado.

## Qué incluye

- **`app.py`** — API REST con **19 endpoints** (FastAPI).
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

## Los 19 endpoints

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
| 16 | GET    | `/orders/search`                      | Buscar órdenes por fecha, cliente o monto |
| 17 | GET    | `/products/{id}/orders`               | Historial de ventas de un producto |
| 18 | GET    | `/stats/sales-by-month`               | Ventas por mes (filtro opcional por año) |
| 19 | POST   | `/products/bulk-adjust`               | Ajustar stock de varios productos (todo o nada) |

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

## Filtros por query string

```bash
# productos: buscar, stock bajo, paginar
/products?q=sail&low_stock=true&limit=10&offset=0

# ordenes: por estado
/orders?status=cancelled&limit=5

# ordenes: busqueda avanzada (endpoint 16)
/orders/search?from=2026-09-01&to=2026-09-30
/orders/search?customer=marina
/orders/search?min_total=1000&status=accepted
```

`from` y `to` son fechas `YYYY-MM-DD` inclusivas; un formato invalido devuelve 400.
`customer` busca coincidencia parcial en nombre o email. Todos los filtros se combinan.

## Desplegar en Render

El `render.yaml` define los dos servicios. Al importar el repo como Blueprint,
Render los crea y pide los valores marcados como `sync: false`.

| | sailtrim-api | sailtrim-mcp |
|---|---|---|
| Start | `uvicorn app:app --host 0.0.0.0 --port $PORT` | `python mcp_server.py` |
| Variables | `API_KEY`, `BEARER_TOKEN` | `API_BASE`, `API_KEY`, `MCP_TRANSPORT`, `MCP_HOST` |

Pasos:

1. Desplegar `sailtrim-api` y cargarle un `API_KEY` y un `BEARER_TOKEN` propios
   (no los de la demo: estan en este repo publico).
2. Copiar la URL que queda (`https://sailtrim-api.onrender.com`) y ponerla como
   `API_BASE` en `sailtrim-mcp`, con el mismo `API_KEY`.

Ambos scripts leen `$PORT`, asi que funcionan igual en local y en Render.

### SQLite en Render

El disco es efimero: `demo.db` se regenera desde el seed en cada deploy y cada
reinicio. Para un demo alcanza. Para conservar datos hace falta un disco pago,
montado y apuntado con `DB_PATH` (ver el comentario en `render.yaml`).

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

Cada test corre contra una base SQLite nueva en un directorio temporal, asi que
nunca tocan `demo.db`.
