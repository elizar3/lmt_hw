CREATE TABLE IF NOT EXISTS bases (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(50) NOT NULL UNIQUE,
  latitude DOUBLE NOT NULL,
  longitude DOUBLE NOT NULL
);

CREATE TABLE IF NOT EXISTS interceptors (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(50) NOT NULL UNIQUE,
  speed_ms INT NOT NULL,
  range_m INT NOT NULL,
  max_altitude_m INT NOT NULL,
  cost_model ENUM('fixed', 'per_minute', 'per_shot') NOT NULL,
  cost_value_eur INT NOT NULL
);

CREATE TABLE IF NOT EXISTS base_inventory (
  base_id INT NOT NULL,
  interceptor_id INT NOT NULL,
  PRIMARY KEY (base_id, interceptor_id),
  FOREIGN KEY (base_id) REFERENCES bases(id),
  FOREIGN KEY (interceptor_id) REFERENCES interceptors(id)
);

INSERT INTO bases (name, latitude, longitude) VALUES
('Riga', 56.97475845607155, 24.1670070219384),
('Liepaja', 56.516083346891044, 21.0182217849017),
('Daugavpils', 55.87409588616014, 26.51864225209475)
ON DUPLICATE KEY UPDATE latitude=VALUES(latitude), longitude=VALUES(longitude);

INSERT INTO interceptors (name, speed_ms, range_m, max_altitude_m, cost_model, cost_value_eur) VALUES
('Interceptor drone', 80, 30000, 2000, 'fixed', 10000),
('Fighter jet', 700, 3500, 15000, 'per_minute', 1000),
('Rocket', 1500, 100000, 30000, 'fixed', 300000),
('50Cal', 900, 2000, 2000, 'per_shot', 1)
ON DUPLICATE KEY UPDATE speed_ms=VALUES(speed_ms), range_m=VALUES(range_m),
  max_altitude_m=VALUES(max_altitude_m), cost_model=VALUES(cost_model), cost_value_eur=VALUES(cost_value_eur);

-- Inventory:
-- Riga has all
INSERT IGNORE INTO base_inventory (base_id, interceptor_id)
SELECT b.id, i.id FROM bases b, interceptors i WHERE b.name='Riga';

-- Daugavpils lacks Fighter jet
INSERT IGNORE INTO base_inventory (base_id, interceptor_id)
SELECT b.id, i.id FROM bases b JOIN interceptors i
WHERE b.name='Daugavpils' AND i.name IN ('Interceptor drone','Rocket','50Cal');

-- Liepaja has only Interceptor drone and 50Cal
INSERT IGNORE INTO base_inventory (base_id, interceptor_id)
SELECT b.id, i.id FROM bases b JOIN interceptors i
WHERE b.name='Liepaja' AND i.name IN ('Interceptor drone','50Cal');
