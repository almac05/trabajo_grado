"""Orquestador nocturno de la prueba piloto (docs/diseno_piloto_proceso_nocturno.md).

Cada noche predice la jornada siguiente (D+1) de las rutas 1 y 3 con el
candidato C3 y genera la recomendacion de despachos.

Modulos:

- ``config``: contrato de configs/piloto/piloto.yaml, entradas congeladas y grupos.
- ``fechas``: hora de Colombia, jornada objetivo y horario sin base de datos.
- ``registro``: log con enmascaramiento de secretos.
- ``extraccion``: ventana de reextraccion, reemplazo por clave y diferencias.
- ``serie``: bloques 4-8 del ETL por ventana y serie de 30 minutos.
- ``prediccion``: franjas de D+1, XGBoost y referencia de 52 semanas.
- ``correccion``: historial de predicciones emitidas y factor de 14 dias.
- ``recomendacion``: modulo de recomendacion sin cambios.
- ``planilla``: archivo Excel de la jornada.
- ``salida_bd``: escritura en bd_montebello_recomendaciones.
- ``salida_s3``: subida de la ejecucion a S3.
- ``estado_s3``: estado entre corridas (almacen e historial) e insumos congelados en S3.
- ``avisos``, ``alerta`` y ``verificacion``: avisos por SNS (exito, fallo de una unidad
  de systemd y vigilante de las 05:00).
- ``nocturno``: orquestador.

Nunca escribe en bd_montebello_rdw ni en bd_montebello_rdw_gps.
"""
