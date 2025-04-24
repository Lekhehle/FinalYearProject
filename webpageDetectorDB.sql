-- MySQL dump 10.13  Distrib 8.0.41, for Linux (x86_64)
--
-- Host: localhost    Database: webpagePhishingDetector
-- ------------------------------------------------------
-- Server version	8.0.41-0ubuntu0.22.04.1

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--

--
-- Table structure for table `phishing_reports`
--

DROP TABLE IF EXISTS `phishing_reports`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `phishing_reports` (
  `id` int NOT NULL AUTO_INCREMENT,
  `url` text NOT NULL,
  `description` text,
  `screenshot` LONGBLOB,
  `reported_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `status` enum('Pending','Verified','Blacklisted') DEFAULT 'Pending',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `phishing_reports`
--

LOCK TABLES `phishing_reports` WRITE;
/*!40000 ALTER TABLE `phishing_reports` DISABLE KEYS */;
/*!40000 ALTER TABLE `phishing_reports` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-04-18 19:18:28

-- Drop existing tables if they exist
DROP TABLE IF EXISTS `phishing_features`;
DROP TABLE IF EXISTS `domain_analysis`;

-- Create optimized phishing_features table
CREATE TABLE `phishing_features` (
  `id` int NOT NULL AUTO_INCREMENT,
  `url` varchar(2048) NOT NULL,
  `url_length` int NOT NULL,
  `num_dots` int NOT NULL,
  `uses_https` tinyint(1) NOT NULL,
  `num_special_chars` int NOT NULL,
  `num_digits` int NOT NULL,
  `has_ip` tinyint(1) NOT NULL,
  `domain_length` int NOT NULL,
  `num_subdomains` int NOT NULL,
  `is_shortened` tinyint(1) NOT NULL,
  `obfuscation_ratio` float NOT NULL,
  `num_hyphens` int NOT NULL,
  `longest_word` int NOT NULL,
  `has_at_symbol` tinyint(1) NOT NULL,
  `has_double_slash` tinyint(1) NOT NULL,
  `suspicious_tld` tinyint(1) NOT NULL,
  `domain` varchar(255) GENERATED ALWAYS AS (
    REGEXP_REPLACE(
      REGEXP_REPLACE(
        REGEXP_REPLACE(url, '^https?://(www\\.)?', ''),
        '/.*$', ''
      ),
      '^[^/]*@', ''
    )
  ) STORED,
  PRIMARY KEY (`id`),
  KEY `idx_domain` (`domain`),
  KEY `idx_has_ip` (`has_ip`),
  KEY `idx_suspicious_tld` (`suspicious_tld`),
  KEY `idx_is_shortened` (`is_shortened`),
  KEY `idx_uses_https` (`uses_https`),
  KEY `idx_risk_factors` (`has_ip`, `suspicious_tld`, `has_at_symbol`, `is_shortened`),
  FULLTEXT KEY `idx_url_fulltext` (`url`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Create a domain analysis table for aggregated statistics
CREATE TABLE `domain_analysis` (
  `domain` varchar(255) NOT NULL,
  `total_urls` int NOT NULL DEFAULT 0,
  `suspicious_count` int NOT NULL DEFAULT 0,
  `avg_obfuscation_ratio` float NOT NULL DEFAULT 0,
  `last_seen` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `risk_score` float GENERATED ALWAYS AS (
    (suspicious_count / total_urls) * 100
  ) STORED,
  PRIMARY KEY (`domain`),
  KEY `idx_risk_score` (`risk_score`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Create a view for high-risk URLs
CREATE OR REPLACE VIEW `high_risk_urls` AS
SELECT 
  pf.id, 
  pf.url, 
  pf.domain,
  (pf.has_ip + pf.suspicious_tld + pf.has_at_symbol + pf.is_shortened + 
   pf.has_double_slash + (1 - pf.uses_https)) AS risk_factors,
  da.risk_score
FROM 
  `phishing_features` pf
JOIN 
  `domain_analysis` da ON pf.domain = da.domain
WHERE 
  pf.has_ip = 1 OR 
  pf.suspicious_tld = 1 OR 
  pf.has_at_symbol = 1 OR
  pf.is_shortened = 1 OR
  da.risk_score > 50
ORDER BY 
  risk_factors DESC, 
  da.risk_score DESC;

-- Create a view to join phishing features with reports
CREATE OR REPLACE VIEW `phishing_analysis` AS
SELECT 
  pf.id AS feature_id,
  pf.url,
  pf.domain,
  pf.has_ip,
  pf.suspicious_tld,
  pf.has_at_symbol,
  pf.is_shortened,
  pf.uses_https,
  pf.obfuscation_ratio,
  da.risk_score,
  pr.id AS report_id,
  pr.description,
  pr.reported_at,
  pr.status
FROM 
  `phishing_features` pf
JOIN 
  `domain_analysis` da ON pf.domain = da.domain
LEFT JOIN 
  `phishing_reports` pr ON pf.url = pr.url
ORDER BY 
  pr.reported_at DESC,
  da.risk_score DESC;

-- Create stored procedure for updating domain analysis
DELIMITER //
DROP PROCEDURE IF EXISTS update_domain_analysis;
CREATE PROCEDURE update_domain_analysis()
BEGIN
  TRUNCATE TABLE domain_analysis;
  INSERT INTO domain_analysis (domain, total_urls, suspicious_count, avg_obfuscation_ratio, last_seen)
  SELECT 
    domain,
    COUNT(*) AS total_urls,
    SUM(CASE WHEN has_ip = 1 OR suspicious_tld = 1 OR has_at_symbol = 1 OR is_shortened = 1 THEN 1 ELSE 0 END) AS suspicious_count,
    AVG(obfuscation_ratio) AS avg_obfuscation_ratio,
    NOW() AS last_seen
  FROM 
    phishing_features
  GROUP BY 
    domain;
  SET @log_message = CONCAT('Domain analysis updated with ', (SELECT COUNT(*) FROM domain_analysis), ' domains');
END //
DELIMITER ;

-- Load data from CSV files into tables (adjust file paths as needed)
LOAD DATA LOCAL INFILE 'phishing-urls.csv'
INTO TABLE phishing_features
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(url, url_length, num_dots, uses_https, num_special_chars, num_digits, has_ip, domain_length, num_subdomains, is_shortened, obfuscation_ratio, num_hyphens, longest_word, has_at_symbol, has_double_slash, suspicious_tld);

-- Removed CSV import for domain_analysis; use stored procedure instead
-- After import, run: CALL update_domain_analysis();
