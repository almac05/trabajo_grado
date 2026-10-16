-- =====================================================================
-- NOTA: Ya aplicado en producción el 2026-10-09; no volver a ejecutar
-- sobre la base existente; el ALTER posterior dejó version_dataset NULL
-- y MAX_USER_CONNECTIONS quedó en 3.
-- =====================================================================
-- =====================================================================
-- Punto 5 — Esquema de recomendaciones (versionado, sin credenciales)
-- Servidor: MySQL 5.7.29, time_zone -05:00
-- Autor: Carlos Alex Macías Perdomo — Trabajo de grado UAO
--
-- Decisiones incorporadas (2026-10-09):
--   * Esquema aparte bd_montebello_recomendaciones. El proceso NUNCA
--     escribe en bd_montebello_rdw ni en bd_montebello_rdw_gps.
--   * Corrida a las 00:30 (opción B del diseño): una sola versión.
--   * El despachador ve demanda predicha y recomendación en Regisdata.
--   * Adherencia: se calcula comparando la recomendación con los
--     despachos reales de bd_montebello_rdw. No hay tabla de adherencia.
--   * fecha = jornada operativa (dia_op). La jornada empieza a las 04:00:
--     las franjas 00:00–03:59 pertenecen a la jornada anterior.
--   * Todas las fechas y horas en hora de Colombia (servidor -05:00).
--
-- Ejecutar por pasos, en una sesión cifrada (HeidiSQL con SSL o túnel SSH).
-- =====================================================================


-- PASO 1 — Esquema ---------------------------------------------------
CREATE DATABASE IF NOT EXISTS bd_montebello_recomendaciones
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE bd_montebello_recomendaciones;


-- PASO 2 — corridas: una fila por ejecución del orquestador ------------
-- Se inserta al iniciar (EN_CURSO) y se actualiza al terminar.
CREATE TABLE IF NOT EXISTS corridas (
  id_corrida            VARCHAR(40)   NOT NULL COMMENT 'AAAAMMDD_HHMMSS (id_ejecucion del diseño). Mismo id que la carpeta local y el prefijo S3',
  fecha_operacion       DATE          NOT NULL COMMENT 'Jornada predicha (D+1)',
  inicio                DATETIME      NOT NULL,
  fin                   DATETIME      NULL,
  estado                ENUM('EN_CURSO','OK','ADVERTENCIA','CONTINGENCIA','ERROR') NOT NULL DEFAULT 'EN_CURSO',
  advertencias          VARCHAR(2000) NULL     COMMENT 'Texto llano, separado por punto y coma',
  entorno               ENUM('EC2','LOCAL') NOT NULL,
  commit_hash           CHAR(40)      NOT NULL,
  version_dataset       CHAR(64)      NULL     COMMENT 'SHA-256 de la serie usada; NULL mientras la corrida está EN_CURSO',
  factor_ruta_1         DECIMAL(8,5)  NULL,
  factor_ruta_3         DECIMAL(8,5)  NULL,
  filas_recomendaciones INT UNSIGNED  NULL,
  ruta_s3               VARCHAR(255)  NULL,
  mensaje_error         VARCHAR(1000) NULL     COMMENT 'Sin credenciales',
  PRIMARY KEY (id_corrida),
  KEY idx_fecha_estado (fecha_operacion, estado, fin)
) ENGINE=InnoDB COMMENT='Registro de ejecuciones del orquestador nocturno';


-- PASO 3 — recomendaciones: una fila por jornada, ruta y franja --------
-- Solo INSERT. Cada corrida inserta sus propias filas; nada se modifica.
CREATE TABLE IF NOT EXISTS recomendaciones (
  id_recomendacion       BIGINT UNSIGNED   NOT NULL AUTO_INCREMENT,
  id_corrida             VARCHAR(40)       NOT NULL,
  fecha                  DATE              NOT NULL COMMENT 'Jornada operativa (dia_op)',
  ruta                   SMALLINT UNSIGNED NOT NULL COMMENT 'FK_RUTA (1 o 3)',
  franja_inicio          TIME              NOT NULL COMMENT 'Inicio de la franja de 30 min',
  franja_fin             TIME              NOT NULL,
  bloque                 VARCHAR(20)       NOT NULL COMMENT 'madrugada, pico_mañana, mañana, valle, pico_tarde, cierre',
  tipo_dia               ENUM('LABORAL','SABADO','DOMINGO','FESTIVO','FESTIVO_PUENTE') NOT NULL,
  regimen                ENUM('ordinario','raro') NOT NULL,
  pasajeros_predichos    DECIMAL(8,2)      NOT NULL COMMENT 'Predicción final (C3 o ref52)',
  divisor                DECIMAL(8,2)      NULL,
  meta_despachos         SMALLINT UNSIGNED NOT NULL COMMENT 'despachos_recomendados (meta final)',
  despachos_si_conductor SMALLINT UNSIGNED NULL     COMMENT 'Columna "Si hay conductor disponible" de la planilla',
  intervalo_sugerido_min DECIMAL(5,1)      NULL,
  dentro_disponibilidad  TINYINT(1)        NOT NULL COMMENT '1 = franja dentro de la disponibilidad habitual',
  grupo                  ENUM('MODULO','CONTROL','SOMBRA') NOT NULL,
  PRIMARY KEY (id_recomendacion),
  UNIQUE KEY uq_corrida_franja (id_corrida, fecha, ruta, franja_inicio),
  KEY idx_fecha_ruta (fecha, ruta, franja_inicio),
  CONSTRAINT fk_reco_corrida FOREIGN KEY (id_corrida) REFERENCES corridas (id_corrida)
) ENGINE=InnoDB COMMENT='Predicción y recomendación de despachos por franja';


-- PASO 4 — Vista oficial que lee Regisdata ---------------------------
-- Por jornada: solo la última corrida terminada en OK, ADVERTENCIA o
-- CONTINGENCIA, y solo filas del grupo MODULO. CONTROL y SOMBRA quedan
-- ocultos por la base de datos. Si la corrida de anoche falló, la
-- jornada de hoy no aparece (no se muestra una recomendación vieja).
-- Uso en Regisdata:  SELECT ... FROM v_recomendaciones_vigentes WHERE fecha = CURDATE()
-- (CURDATE() es hora Colombia porque el servidor está en -05:00;
--  entre 00:00 y 03:59 la jornada en curso es CURDATE() - 1).
CREATE OR REPLACE VIEW v_recomendaciones_vigentes AS
SELECT
  r.fecha, r.ruta, r.franja_inicio, r.franja_fin, r.bloque,
  r.tipo_dia, r.regimen,
  r.pasajeros_predichos, r.meta_despachos, r.despachos_si_conductor,
  r.intervalo_sugerido_min, r.dentro_disponibilidad,
  c.estado AS estado_corrida, c.advertencias, r.id_corrida
FROM recomendaciones r
JOIN corridas c ON c.id_corrida = r.id_corrida
WHERE c.estado IN ('OK','ADVERTENCIA','CONTINGENCIA')
  AND r.grupo = 'MODULO'
  AND NOT EXISTS (
    SELECT 1 FROM corridas c2
    WHERE c2.fecha_operacion = c.fecha_operacion
      AND c2.estado IN ('OK','ADVERTENCIA','CONTINGENCIA')
      AND c2.fin > c.fin
  );

-- Vista de prueba para el modo sombra (13–18 oct): igual, pero incluye
-- SOMBRA. Solo para la pantalla de pruebas de Registel, nunca para el
-- despachador.
CREATE OR REPLACE VIEW v_recomendaciones_prueba AS
SELECT
  r.fecha, r.ruta, r.franja_inicio, r.franja_fin, r.bloque,
  r.tipo_dia, r.regimen,
  r.pasajeros_predichos, r.meta_despachos, r.despachos_si_conductor,
  r.intervalo_sugerido_min, r.dentro_disponibilidad,
  r.grupo, c.estado AS estado_corrida, c.advertencias, r.id_corrida
FROM recomendaciones r
JOIN corridas c ON c.id_corrida = r.id_corrida
WHERE c.estado IN ('OK','ADVERTENCIA','CONTINGENCIA')
  AND r.grupo IN ('MODULO','SOMBRA')
  AND NOT EXISTS (
    SELECT 1 FROM corridas c2
    WHERE c2.fecha_operacion = c.fecha_operacion
      AND c2.estado IN ('OK','ADVERTENCIA','CONTINGENCIA')
      AND c2.fin > c.fin
  );


-- PASO 5 — Usuario del orquestador -----------------------------------
-- Solo desde 127.0.0.1 (túnel SSH o sesión en el propio servidor).
-- Desde internet NO puede entrar aunque el 3306 esté abierto.
-- Reemplazar <CONTRASENA_LARGA> (32+ caracteres aleatorios). No guardarla
-- en el repositorio ni en archivos que se suban a S3.
CREATE USER IF NOT EXISTS 'reco_proceso'@'127.0.0.1'
  IDENTIFIED BY '<CONTRASENA_LARGA>'
  WITH MAX_USER_CONNECTIONS 5;

GRANT SELECT ON bd_montebello_rdw.*     TO 'reco_proceso'@'127.0.0.1';
GRANT SELECT ON bd_montebello_rdw_gps.* TO 'reco_proceso'@'127.0.0.1';
GRANT SELECT, INSERT, UPDATE ON bd_montebello_recomendaciones.corridas        TO 'reco_proceso'@'127.0.0.1';
GRANT SELECT, INSERT         ON bd_montebello_recomendaciones.recomendaciones TO 'reco_proceso'@'127.0.0.1';
GRANT SELECT ON bd_montebello_recomendaciones.v_recomendaciones_vigentes TO 'reco_proceso'@'127.0.0.1';
GRANT SELECT ON bd_montebello_recomendaciones.v_recomendaciones_prueba   TO 'reco_proceso'@'127.0.0.1';


-- PASO 6 (cuando Registel confirme usuario e IP de Regisdata) ----------
-- Solo lectura de las vistas. Reemplazar <USUARIO_REGISDATA> e <IP>.
-- GRANT SELECT ON bd_montebello_recomendaciones.v_recomendaciones_vigentes TO '<USUARIO_REGISDATA>'@'<IP>';
-- GRANT SELECT ON bd_montebello_recomendaciones.v_recomendaciones_prueba   TO '<USUARIO_REGISDATA>'@'<IP>';


-- PASO 7 — Verificación ----------------------------------------------
SHOW GRANTS FOR 'reco_proceso'@'127.0.0.1';
SHOW FULL TABLES FROM bd_montebello_recomendaciones;
-- Prueba negativa, conectado COMO reco_proceso desde el servidor
-- (mysql -h 127.0.0.1 -u reco_proceso -p). Ambas deben fallar:
--   CREATE TABLE bd_montebello_rdw.prueba (x INT);
--   DELETE FROM bd_montebello_recomendaciones.recomendaciones;


-- REVERSIÓN (no toca bd_montebello_rdw) --------------------------------
-- DROP USER IF EXISTS 'reco_proceso'@'127.0.0.1';
-- DROP DATABASE IF EXISTS bd_montebello_recomendaciones;
