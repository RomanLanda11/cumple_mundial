# Contexto para agentes

Este repo contiene una app Streamlit para manejar el juego "Cumple Mundial", pensado para usar durante el cumpleanos de Roman.

## Objetivo de la app

La app tiene que permitir administrar un torneo de eliminacion directa mientras llegan invitados. La carga principal se hace desde el celular y el cuadro se puede mirar desde una computadora.

El flujo esperado es:

1. Abrir la app en modo inscripcion.
2. Cargar participantes a medida que van llegando.
3. Cuando ya estan todos, sortear el cuadro.
4. Jugar las eliminatorias.
5. Cargar ganador de cada partido.
6. Asignar representante a cada eliminado.
7. Avanzar ronda cuando todo este cerrado.
8. Llegar a una final con dos finalistas, cada uno con su bando.
9. Mostrar campeon y equipos/bandos finales.

## Reglas del juego

- La cantidad exacta de gente no se sabe de antemano.
- Se espera entre 35 y 60 personas.
- Al sortear, la inscripcion se cierra.
- Los que llegan tarde despues del sorteo no entran al cuadro.
- El cuadro debe adaptarse automaticamente a la cantidad real de participantes.
- Si la cantidad no es potencia de 2, se usan byes automaticos.
- Los participantes se ordenan aleatoriamente en el cuadro.
- Dos personas se enfrentan por partido.
- El ganador avanza a la siguiente fase.
- El ganador tiene que hacer "medio fondo blanco" de lo que este tomando.
- El perdedor queda eliminado como jugador, pero mantiene interes en el torneo.
- El perdedor elige una persona viva/clasificada para que lo represente.
- Una vez elegido su representante, queda atado a esa cadena.
- Ejemplo: Roman pierde contra Martina. Martina avanza. Roman puede elegir a Franco si Franco tambien paso de ronda.
- Si Franco gana, Roman sigue avanzando con Franco.
- Si Franco pierde, Roman pasa a depender de la eleccion que haga Franco.
- Al final hay dos finalistas, cada uno con su bando.
- El campeon gana premio individual.
- El bando del campeon gana premios grupales.

## Decisiones de producto ya tomadas

- Persistencia local con SQLite en `data/tournament.db`.
- App levantada con Streamlit desde `app.py`.
- No hace falta deploy automatico.
- El usuario va a levantarla manualmente con:

```powershell
python -m streamlit run app.py
```

- La UI debe funcionar bien en celular para cargar gente y controlar la ronda.
- La UI debe ser legible en computadora para ver el cuadro.
- El diseno apunta a una mesa/cancha de torneo: fondo de cancha, tarjetas claras, acento amarillo.
- Evitar una landing page; la primera pantalla debe ser la experiencia usable.

## Estructura del repo

- `app.py`: UI principal de Streamlit.
- `src/db.py`: conexion SQLite, schema y operaciones de base.
- `src/models.py`: dataclasses y enums.
- `src/tournament.py`: reglas del torneo, sorteo, byes, avance de rondas y representantes.
- `src/ui.py`: tema visual y componentes de UI.
- `tests/test_tournament.py`: tests de reglas principales.
- `.streamlit/config.toml`: configuracion de Streamlit y tema claro.
- `requirements.txt`: dependencias.
- `README.md`: instrucciones para instalar y correr.

## Verificacion recomendada

Antes de entregar cambios, correr:

```powershell
python -m py_compile app.py src\db.py src\ui.py src\tournament.py src\models.py
python -m pytest tests -q -p no:cacheprovider
```

## Consideraciones importantes

- Streamlit puede mantener modulos viejos en memoria. Si aparece un error raro despues de cambios de firma, frenar con `Ctrl+C` y levantar de nuevo.
- No compartir una conexion SQLite cacheada entre threads de Streamlit.
- La conexion SQLite usa `check_same_thread=False`.
- No avanzar una ronda si hay partidos abiertos.
- No avanzar una ronda si quedan perdedores sin representante.
- No cambiar las reglas de representantes sin actualizar tests.
- Mantener la app simple y rapida de operar durante una fiesta.
