# Cumple Mundial - contexto para Claude

Este proyecto es una app Streamlit para administrar un juego de cumpleanos llamado "Cumple Mundial".

## Que esta construyendo el usuario

Roman quiere usar esta app durante su cumple. A medida que llegan invitados, va cargando sus nombres desde el celular. Cuando ya estan todos, sortea un cuadro de eliminacion directa que despues se puede ver y controlar desde una computadora.

La app no es una pagina de marketing. Es una herramienta de uso real durante una fiesta: debe ser clara, rapida, resistente a errores y facil de operar con ruido, gente alrededor y desde celular.

## Regla central

Es un torneo eliminatorio adaptable para unas 35 a 60 personas.

Cada partido enfrenta a dos participantes. El ganador avanza y hace medio fondo blanco de lo que este tomando. El perdedor no sigue jugando, pero elige un representante entre quienes siguen vivos en la ronda.

Esa eleccion crea una cadena:

- Roman pierde.
- Roman elige a Franco como representante.
- Si Franco gana, Roman sigue en el bando de Franco.
- Si Franco pierde y Franco elige a Martina, Roman tambien pasa a depender de Martina.

El torneo termina con dos finalistas y sus bandos. Hay premio individual para el campeon y premios grupales para el bando ganador.

## Flujo de uso

1. Inscripcion abierta.
2. Cargar participantes por nombre.
3. Sortear cuadro cuando ya estan todos.
4. La inscripcion queda cerrada.
5. La app arma un bracket a la siguiente potencia de 2.
6. Si sobran lugares, la app asigna byes automaticos.
7. En cada ronda se cargan resultados.
8. Cada perdedor debe elegir representante.
9. Solo se puede avanzar de ronda cuando todos los partidos estan cerrados y todos los perdedores tienen representante.
10. Al terminar, se muestra campeon y bandos.

## Stack

- Python
- Streamlit
- SQLite local
- Pytest

## Archivos principales

- `app.py`: pantallas y flujo Streamlit.
- `src/db.py`: schema SQLite y CRUD.
- `src/models.py`: modelos de datos.
- `src/tournament.py`: logica del juego.
- `src/ui.py`: CSS y componentes visuales.
- `tests/test_tournament.py`: cobertura de reglas.

## Comandos utiles

Instalar:

```powershell
pip install -r requirements.txt
```

Correr:

```powershell
python -m streamlit run app.py
```

Validar:

```powershell
python -m py_compile app.py src\db.py src\ui.py src\tournament.py src\models.py
python -m pytest tests -q -p no:cacheprovider
```

## Decisiones ya tomadas

- La base se guarda en `data/tournament.db`.
- El estado es local; no hay backend remoto.
- No hace falta levantar servidor automaticamente desde el agente.
- El usuario prefiere levantar Streamlit manualmente.
- La app tiene que servir tanto para celular como para desktop.
- La UI debe ser directa y funcional, no decorativa.
- El estilo visual actual usa una identidad de cancha/planilla de torneo.

## Riesgos a cuidar

- Streamlit puede cachear modulos; si algo no cambia en pantalla, reiniciar el proceso.
- SQLite en Streamlit no debe usar una conexion cacheada comun entre threads.
- No permitir avanzar si falta asignar representantes.
- No permitir elegir representantes que no esten vivos/clasificados.
- Los cambios de reglas deben venir acompanados por tests.
- Mantener los textos simples porque la app se usa en contexto de fiesta.
