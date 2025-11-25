-- Seed test users for Lobby Maker testing
-- Run this with: psql -U your_user -d your_database -f seed_test_users.sql

-- Insert 20 test users with realistic battletags
INSERT INTO users (battlenet_id, battletag, name, email, battlegrounds_rating, role, is_active, settings, favorite_lobby_makers)
VALUES
  ('TEST001', 'ProGamer#1234', 'Alex Johnson', 'alex@test.com', 8500, 'user', true, '{}', NULL),
  ('TEST002', 'DragonSlayer#5678', 'Maria Garcia', 'maria@test.com', 7800, 'user', true, '{}', NULL),
  ('TEST003', 'NightHawk#9012', 'John Smith', 'john@test.com', 9200, 'premium', true, '{}', NULL),
  ('TEST004', 'ShadowBlade#3456', 'Emma Wilson', 'emma@test.com', 6500, 'user', true, '{}', NULL),
  ('TEST005', 'ThunderStrike#7890', 'Michael Brown', 'michael@test.com', 8100, 'user', true, '{}', NULL),
  ('TEST006', 'IceQueen#2345', 'Sofia Martinez', 'sofia@test.com', 7500, 'premium', true, '{}', NULL),
  ('TEST007', 'FireStorm#6789', 'David Lee', 'david@test.com', 8800, 'user', true, '{}', NULL),
  ('TEST008', 'MysticMage#0123', 'Olivia Taylor', 'olivia@test.com', 7200, 'user', true, '{}', NULL),
  ('TEST009', 'StealthNinja#4567', 'James Anderson', 'james@test.com', 9000, 'premium', true, '{}', NULL),
  ('TEST010', 'CrimsonKnight#8901', 'Isabella Thomas', 'isabella@test.com', 6800, 'user', true, '{}', NULL),
  ('TEST011', 'GoldenEagle#2346', 'William Jackson', 'william@test.com', 8300, 'user', true, '{}', NULL),
  ('TEST012', 'SilverWolf#6780', 'Ava White', 'ava@test.com', 7600, 'premium', true, '{}', NULL),
  ('TEST013', 'PhoenixRising#0124', 'Robert Harris', 'robert@test.com', 8900, 'user', true, '{}', NULL),
  ('TEST014', 'VenomStrike#4568', 'Mia Martin', 'mia@test.com', 7100, 'user', true, '{}', NULL),
  ('TEST015', 'TitanForce#8902', 'Daniel Thompson', 'daniel@test.com', 8600, 'premium', true, '{}', NULL),
  ('TEST016', 'LunarEclipse#2347', 'Charlotte Garcia', 'charlotte@test.com', 7400, 'user', true, '{}', NULL),
  ('TEST017', 'SolarFlare#6781', 'Joseph Martinez', 'joseph@test.com', 8200, 'user', true, '{}', NULL),
  ('TEST018', 'CosmicRay#0125', 'Amelia Robinson', 'amelia@test.com', 7700, 'premium', true, '{}', NULL),
  ('TEST019', 'QuantumLeap#4569', 'Christopher Clark', 'chris@test.com', 9100, 'user', true, '{}', NULL),
  ('TEST020', 'NebulaDrift#8903', 'Harper Rodriguez', 'harper@test.com', 6900, 'user', true, '{}', NULL)
ON CONFLICT (battlenet_id) DO NOTHING;

-- Verify insertion
SELECT COUNT(*) as test_users_count FROM users WHERE battlenet_id LIKE 'TEST%';

-- Show all test users
SELECT id, battlenet_id, battletag, name, battlegrounds_rating, role 
FROM users 
WHERE battlenet_id LIKE 'TEST%'
ORDER BY id;
