# EVOFIT Fitness (React)

Frontend premium tipo app para la sección fitness (React + Tailwind + Framer Motion).

## Requisitos

- Node.js 18+

## Correr

1) En otra terminal, levanta el backend Flask (puerto 5000).
2) En `frontend/`:

```bash
npm install
npm run dev
```

## Login

La UI consume la API en el mismo dominio (`/api/...`) usando cookies de sesión (`credentials: 'include'`).

- Entra primero al login del backend: `http://127.0.0.1:5000/login`
- Luego abre: `http://127.0.0.1:5173`
