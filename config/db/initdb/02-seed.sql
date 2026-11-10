-- Datos de ejemplo para que la base de datos tenga actividad que monitorear
USE laboratorio;
CREATE TABLE IF NOT EXISTS visitas (
  id INT AUTO_INCREMENT PRIMARY KEY,
  origen VARCHAR(50) NOT NULL,
  creado TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO visitas (origen) VALUES ('seed-1'), ('seed-2'), ('seed-3');
