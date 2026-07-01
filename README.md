# Cumple Mundial

App Streamlit para manejar una eliminatoria adaptable de cumpleanos: carga de participantes, sorteo del cuadro, resultados, representantes y bandos.

## Instalacion

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Uso

```powershell
streamlit run app.py
```

La app guarda el estado en `data/tournament.db`. Para usarla desde el celular, levanta Streamlit en la computadora y entra desde el telefono a la URL de red local que muestra Streamlit.

## Reglas implementadas

- El torneo empieza en modo inscripcion.
- Al sortear, se cierra la inscripcion y se arma un cuadro a la siguiente potencia de 2.
- Los lugares vacios son byes automaticos al azar.
- Cada partido tiene ganador, nota opcional y marca de prenda.
- El perdedor elige representante entre los clasificados vivos de la ronda actual.
- No se puede avanzar de ronda hasta cerrar todos los partidos y asignar todos los representantes.
- Al final se muestran campeon y bandos.
