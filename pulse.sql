-- MySQL dump 10.13  Distrib 8.0.45, for Win64 (x86_64)
--
-- Host: localhost    Database: u520834156_dbPulse
-- ------------------------------------------------------
-- Server version	8.0.45

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;
--
-- Table structure for table `admin`
--

DROP TABLE IF EXISTS `admin`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `admin` (
  `admin_id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `email` varchar(254) NOT NULL,
  `password` varchar(255) NOT NULL,
  `role` varchar(50) NOT NULL,
  `status` varchar(50) NOT NULL,
  PRIMARY KEY (`admin_id`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `admin`
--

LOCK TABLES `admin` WRITE;
/*!40000 ALTER TABLE `admin` DISABLE KEYS */;
/*!40000 ALTER TABLE `admin` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `admins`
--

DROP TABLE IF EXISTS `admins`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `admins` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `username` varchar(100) NOT NULL,
  `first_name` varchar(100) NOT NULL,
  `last_name` varchar(100) NOT NULL,
  `middle_name` varchar(100) DEFAULT NULL,
  `suffix` varchar(20) DEFAULT NULL,
  `email` varchar(255) NOT NULL,
  `contact_number` varchar(20) DEFAULT NULL,
  `assigned_office` varchar(150) DEFAULT NULL,
  `password_hash` varchar(255) NOT NULL,
  `profile_image` varchar(500) DEFAULT NULL,
  `status` varchar(10) NOT NULL,
  `remember_token` varchar(255) DEFAULT NULL,
  `token_expiry` datetime(6) DEFAULT NULL,
  `last_login` datetime(6) DEFAULT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `admins`
--

LOCK TABLES `admins` WRITE;
/*!40000 ALTER TABLE `admins` DISABLE KEYS */;
INSERT INTO `admins` VALUES (1,'admin','System','Administrator',NULL,NULL,'admin@pulse.local',NULL,'Bago City Health Office','$2b$12$JlHj6Rb45DfBbFXUrX421OQy91I0t5d19/RTSacqp/bgOMNCV9EuS',NULL,'active',NULL,NULL,'2026-07-02 15:26:07.918449','2026-06-10 15:47:29.945801','2026-06-10 15:47:29.945801');
/*!40000 ALTER TABLE `admins` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `alerts`
--

DROP TABLE IF EXISTS `alerts`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `alerts` (
  `alert_id` int NOT NULL AUTO_INCREMENT,
  `alert_level` varchar(50) NOT NULL,
  `alert_date` datetime(6) NOT NULL,
  `status` varchar(50) NOT NULL,
  `alert_type` varchar(100) NOT NULL,
  `analysis_id` int NOT NULL,
  PRIMARY KEY (`alert_id`),
  KEY `alerts_analysis_id_ea1c020a_fk_risk_analysis_analysis_id` (`analysis_id`),
  CONSTRAINT `alerts_analysis_id_ea1c020a_fk_risk_analysis_analysis_id` FOREIGN KEY (`analysis_id`) REFERENCES `risk_analysis` (`analysis_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `alerts`
--

LOCK TABLES `alerts` WRITE;
/*!40000 ALTER TABLE `alerts` DISABLE KEYS */;
/*!40000 ALTER TABLE `alerts` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `audit_logs`
--

DROP TABLE IF EXISTS `audit_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_logs` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `actor_id` int unsigned DEFAULT NULL,
  `actor_type` varchar(15) NOT NULL,
  `action` varchar(100) NOT NULL,
  `target_id` int unsigned DEFAULT NULL,
  `details` longtext,
  `created_at` datetime(6) NOT NULL,
  `actor_display_name` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  CONSTRAINT `audit_logs_chk_1` CHECK ((`actor_id` >= 0)),
  CONSTRAINT `audit_logs_chk_2` CHECK ((`target_id` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `audit_logs`
--

LOCK TABLES `audit_logs` WRITE;
/*!40000 ALTER TABLE `audit_logs` DISABLE KEYS */;
INSERT INTO `audit_logs` VALUES (1,1,'admin','report_validated',1,NULL,'2026-06-13 13:24:22.901518',NULL),(2,1,'admin','case_confirmed',1,NULL,'2026-06-13 13:24:32.421522',NULL),(3,1,'admin','report_validated',3,NULL,'2026-06-15 07:15:51.862325',NULL),(4,1,'admin','report_validated',2,NULL,'2026-06-19 07:22:58.056893',NULL),(5,1,'admin','case_confirmed',4,NULL,'2026-06-25 14:05:53.846372','System Administrator');
/*!40000 ALTER TABLE `audit_logs` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_group`
--

DROP TABLE IF EXISTS `auth_group`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_group` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(150) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_group`
--

LOCK TABLES `auth_group` WRITE;
/*!40000 ALTER TABLE `auth_group` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_group` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_group_permissions`
--

DROP TABLE IF EXISTS `auth_group_permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_group_permissions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `group_id` int NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_group_permissions_group_id_permission_id_0cd325b0_uniq` (`group_id`,`permission_id`),
  KEY `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` (`permission_id`),
  CONSTRAINT `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `auth_group_permissions_group_id_b120cbf9_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_group_permissions`
--

LOCK TABLES `auth_group_permissions` WRITE;
/*!40000 ALTER TABLE `auth_group_permissions` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_group_permissions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_permission`
--

DROP TABLE IF EXISTS `auth_permission`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_permission` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `content_type_id` int NOT NULL,
  `codename` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_permission_content_type_id_codename_01ab375a_uniq` (`content_type_id`,`codename`),
  CONSTRAINT `auth_permission_content_type_id_2f476e4b_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=161 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_permission`
--

LOCK TABLES `auth_permission` WRITE;
/*!40000 ALTER TABLE `auth_permission` DISABLE KEYS */;
INSERT INTO `auth_permission` VALUES (1,'Can add log entry',1,'add_logentry'),(2,'Can change log entry',1,'change_logentry'),(3,'Can delete log entry',1,'delete_logentry'),(4,'Can view log entry',1,'view_logentry'),(5,'Can add permission',3,'add_permission'),(6,'Can change permission',3,'change_permission'),(7,'Can delete permission',3,'delete_permission'),(8,'Can view permission',3,'view_permission'),(9,'Can add group',2,'add_group'),(10,'Can change group',2,'change_group'),(11,'Can delete group',2,'delete_group'),(12,'Can view group',2,'view_group'),(13,'Can add user',4,'add_user'),(14,'Can change user',4,'change_user'),(15,'Can delete user',4,'delete_user'),(16,'Can view user',4,'view_user'),(17,'Can add content type',5,'add_contenttype'),(18,'Can change content type',5,'change_contenttype'),(19,'Can delete content type',5,'delete_contenttype'),(20,'Can view content type',5,'view_contenttype'),(21,'Can add session',6,'add_session'),(22,'Can change session',6,'change_session'),(23,'Can delete session',6,'delete_session'),(24,'Can view session',6,'view_session'),(25,'Can add admin',7,'add_admin'),(26,'Can change admin',7,'change_admin'),(27,'Can delete admin',7,'delete_admin'),(28,'Can view admin',7,'view_admin'),(29,'Can add alerts',8,'add_alerts'),(30,'Can change alerts',8,'change_alerts'),(31,'Can delete alerts',8,'delete_alerts'),(32,'Can view alerts',8,'view_alerts'),(33,'Can add barangays',9,'add_barangays'),(34,'Can change barangays',9,'change_barangays'),(35,'Can delete barangays',9,'delete_barangays'),(36,'Can view barangays',9,'view_barangays'),(37,'Can add ml ai predictions',15,'add_mlaipredictions'),(38,'Can change ml ai predictions',15,'change_mlaipredictions'),(39,'Can delete ml ai predictions',15,'delete_mlaipredictions'),(40,'Can view ml ai predictions',15,'view_mlaipredictions'),(41,'Can add super admin',19,'add_superadmin'),(42,'Can change super admin',19,'change_superadmin'),(43,'Can delete super admin',19,'delete_superadmin'),(44,'Can view super admin',19,'view_superadmin'),(45,'Can add bhw',10,'add_bhw'),(46,'Can change bhw',10,'change_bhw'),(47,'Can delete bhw',10,'delete_bhw'),(48,'Can view bhw',10,'view_bhw'),(49,'Can add environment data',11,'add_environmentdata'),(50,'Can change environment data',11,'change_environmentdata'),(51,'Can delete environment data',11,'delete_environmentdata'),(52,'Can view environment data',11,'view_environmentdata'),(53,'Can add health report',12,'add_healthreport'),(54,'Can change health report',12,'change_healthreport'),(55,'Can delete health report',12,'delete_healthreport'),(56,'Can view health report',12,'view_healthreport'),(57,'Can add notification',16,'add_notification'),(58,'Can change notification',16,'change_notification'),(59,'Can delete notification',16,'delete_notification'),(60,'Can view notification',16,'view_notification'),(61,'Can add patients',17,'add_patients'),(62,'Can change patients',17,'change_patients'),(63,'Can delete patients',17,'delete_patients'),(64,'Can view patients',17,'view_patients'),(65,'Can add incident report',14,'add_incidentreport'),(66,'Can change incident report',14,'change_incidentreport'),(67,'Can delete incident report',14,'delete_incidentreport'),(68,'Can view incident report',14,'view_incidentreport'),(69,'Can add historical records',13,'add_historicalrecords'),(70,'Can change historical records',13,'change_historicalrecords'),(71,'Can delete historical records',13,'delete_historicalrecords'),(72,'Can view historical records',13,'view_historicalrecords'),(73,'Can add risk analysis',18,'add_riskanalysis'),(74,'Can change risk analysis',18,'change_riskanalysis'),(75,'Can delete risk analysis',18,'delete_riskanalysis'),(76,'Can view risk analysis',18,'view_riskanalysis'),(77,'Can add audit log',21,'add_auditlog'),(78,'Can change audit log',21,'change_auditlog'),(79,'Can delete audit log',21,'delete_auditlog'),(80,'Can view audit log',21,'view_auditlog'),(81,'Can add login attempt',24,'add_loginattempt'),(82,'Can change login attempt',24,'change_loginattempt'),(83,'Can delete login attempt',24,'delete_loginattempt'),(84,'Can view login attempt',24,'view_loginattempt'),(85,'Can add system log',30,'add_systemlog'),(86,'Can change system log',30,'change_systemlog'),(87,'Can delete system log',30,'delete_systemlog'),(88,'Can view system log',30,'view_systemlog'),(89,'Can add pulse session',32,'add_pulsesession'),(90,'Can change pulse session',32,'change_pulsesession'),(91,'Can delete pulse session',32,'delete_pulsesession'),(92,'Can view pulse session',32,'view_pulsesession'),(93,'Can add patient case',33,'add_patientcase'),(94,'Can change patient case',33,'change_patientcase'),(95,'Can delete patient case',33,'delete_patientcase'),(96,'Can view patient case',33,'view_patientcase'),(97,'Can add symptom',35,'add_symptom'),(98,'Can change symptom',35,'change_symptom'),(99,'Can delete symptom',35,'delete_symptom'),(100,'Can view symptom',35,'view_symptom'),(101,'Can add user',31,'add_user'),(102,'Can change user',31,'change_user'),(103,'Can delete user',31,'delete_user'),(104,'Can view user',31,'view_user'),(105,'Can add surveillance report',29,'add_surveillancereport'),(106,'Can change surveillance report',29,'change_surveillancereport'),(107,'Can delete surveillance report',29,'delete_surveillancereport'),(108,'Can view surveillance report',29,'view_surveillancereport'),(109,'Can add surveillance session',34,'add_surveillancesession'),(110,'Can change surveillance session',34,'change_surveillancesession'),(111,'Can delete surveillance session',34,'delete_surveillancesession'),(112,'Can view surveillance session',34,'view_surveillancesession'),(113,'Can add alert',20,'add_alert'),(114,'Can change alert',20,'change_alert'),(115,'Can delete alert',20,'delete_alert'),(116,'Can view alert',20,'view_alert'),(117,'Can add risk assessment',28,'add_riskassessment'),(118,'Can change risk assessment',28,'change_riskassessment'),(119,'Can delete risk assessment',28,'delete_riskassessment'),(120,'Can view risk assessment',28,'view_riskassessment'),(121,'Can add ocr result',26,'add_ocrresult'),(122,'Can change ocr result',26,'change_ocrresult'),(123,'Can delete ocr result',26,'delete_ocrresult'),(124,'Can view ocr result',26,'view_ocrresult'),(125,'Can add barangay',22,'add_barangay'),(126,'Can change barangay',22,'change_barangay'),(127,'Can delete barangay',22,'delete_barangay'),(128,'Can view barangay',22,'view_barangay'),(129,'Can add environmental data',23,'add_environmentaldata'),(130,'Can change environmental data',23,'change_environmentaldata'),(131,'Can delete environmental data',23,'delete_environmentaldata'),(132,'Can view environmental data',23,'view_environmentaldata'),(133,'Can add registration request',27,'add_registrationrequest'),(134,'Can change registration request',27,'change_registrationrequest'),(135,'Can delete registration request',27,'delete_registrationrequest'),(136,'Can view registration request',27,'view_registrationrequest'),(137,'Can add notification log',25,'add_notificationlog'),(138,'Can change notification log',25,'change_notificationlog'),(139,'Can delete notification log',25,'delete_notificationlog'),(140,'Can view notification log',25,'view_notificationlog'),(141,'Can add mitigation protocol',36,'add_mitigationprotocol'),(142,'Can change mitigation protocol',36,'change_mitigationprotocol'),(143,'Can delete mitigation protocol',36,'delete_mitigationprotocol'),(144,'Can view mitigation protocol',36,'view_mitigationprotocol'),(145,'Can add disease category threshold',38,'add_diseasecategorythreshold'),(146,'Can change disease category threshold',38,'change_diseasecategorythreshold'),(147,'Can delete disease category threshold',38,'delete_diseasecategorythreshold'),(148,'Can view disease category threshold',38,'view_diseasecategorythreshold'),(149,'Can add barangay epidemic status',37,'add_barangayepidemicstatus'),(150,'Can change barangay epidemic status',37,'change_barangayepidemicstatus'),(151,'Can delete barangay epidemic status',37,'delete_barangayepidemicstatus'),(152,'Can view barangay epidemic status',37,'view_barangayepidemicstatus'),(153,'Can add outbreak threshold log',39,'add_outbreakthresholdlog'),(154,'Can change outbreak threshold log',39,'change_outbreakthresholdlog'),(155,'Can delete outbreak threshold log',39,'delete_outbreakthresholdlog'),(156,'Can view outbreak threshold log',39,'view_outbreakthresholdlog'),(157,'Can add barangay risk log',40,'add_barangayrisklog'),(158,'Can change barangay risk log',40,'change_barangayrisklog'),(159,'Can delete barangay risk log',40,'delete_barangayrisklog'),(160,'Can view barangay risk log',40,'view_barangayrisklog');
/*!40000 ALTER TABLE `auth_permission` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_user`
--

DROP TABLE IF EXISTS `auth_user`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_user` (
  `id` int NOT NULL AUTO_INCREMENT,
  `password` varchar(128) NOT NULL,
  `last_login` datetime(6) DEFAULT NULL,
  `is_superuser` tinyint(1) NOT NULL,
  `username` varchar(150) NOT NULL,
  `first_name` varchar(150) NOT NULL,
  `last_name` varchar(150) NOT NULL,
  `email` varchar(254) NOT NULL,
  `is_staff` tinyint(1) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `date_joined` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_user`
--

LOCK TABLES `auth_user` WRITE;
/*!40000 ALTER TABLE `auth_user` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_user` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_user_groups`
--

DROP TABLE IF EXISTS `auth_user_groups`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_user_groups` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `group_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_user_groups_user_id_group_id_94350c0c_uniq` (`user_id`,`group_id`),
  KEY `auth_user_groups_group_id_97559544_fk_auth_group_id` (`group_id`),
  CONSTRAINT `auth_user_groups_group_id_97559544_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`),
  CONSTRAINT `auth_user_groups_user_id_6a12ed8b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_user_groups`
--

LOCK TABLES `auth_user_groups` WRITE;
/*!40000 ALTER TABLE `auth_user_groups` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_user_groups` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_user_user_permissions`
--

DROP TABLE IF EXISTS `auth_user_user_permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_user_user_permissions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_user_user_permissions_user_id_permission_id_14a6b632_uniq` (`user_id`,`permission_id`),
  KEY `auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm` (`permission_id`),
  CONSTRAINT `auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_user_user_permissions`
--

LOCK TABLES `auth_user_user_permissions` WRITE;
/*!40000 ALTER TABLE `auth_user_user_permissions` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_user_user_permissions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `barangay_epidemic_statuses`
--

DROP TABLE IF EXISTS `barangay_epidemic_statuses`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `barangay_epidemic_statuses` (
  `id` int NOT NULL AUTO_INCREMENT,
  `disease_label` varchar(150) NOT NULL,
  `pidsr_category` varchar(32) NOT NULL,
  `threshold_status` varchar(32) NOT NULL,
  `confirmed_count` smallint unsigned NOT NULL,
  `evaluated_at` datetime(6) NOT NULL,
  `barangay_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_barangay_disease_epidemic_status` (`barangay_id`,`disease_label`),
  CONSTRAINT `barangay_epidemic_statuses_chk_1` CHECK ((`confirmed_count` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `barangay_epidemic_statuses`
--

LOCK TABLES `barangay_epidemic_statuses` WRITE;
/*!40000 ALTER TABLE `barangay_epidemic_statuses` DISABLE KEYS */;
INSERT INTO `barangay_epidemic_statuses` VALUES (1,'Undetermined','Category 2','ISOLATED_CASE',1,'2026-06-25 14:05:53.805815',20);
/*!40000 ALTER TABLE `barangay_epidemic_statuses` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `barangay_risk_logs`
--

DROP TABLE IF EXISTS `barangay_risk_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `barangay_risk_logs` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `barangay` varchar(100) NOT NULL,
  `syndrome` varchar(100) NOT NULL,
  `anomaly_score` double NOT NULL,
  `temporal_score` double NOT NULL,
  `environmental_score` double NOT NULL,
  `spatial_score` double NOT NULL,
  `final_risk_score` double NOT NULL,
  `risk_level` varchar(20) NOT NULL,
  `is_active_alert` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `barangay_ri_baranga_cb1564_idx` (`barangay`,`syndrome`),
  KEY `barangay_ri_is_acti_5c3905_idx` (`is_active_alert`,`created_at` DESC)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `barangay_risk_logs`
--

LOCK TABLES `barangay_risk_logs` WRITE;
/*!40000 ALTER TABLE `barangay_risk_logs` DISABLE KEYS */;
INSERT INTO `barangay_risk_logs` VALUES (1,'Poblacion','Dengue',0.92,0,0.4994,0,53.49,'High',1,'2026-06-23 14:23:01.430284');
/*!40000 ALTER TABLE `barangay_risk_logs` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `barangays`
--

DROP TABLE IF EXISTS `barangays`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `barangays` (
  `barangay_id` int NOT NULL AUTO_INCREMENT,
  `barangay_name` varchar(100) NOT NULL,
  `city` varchar(100) NOT NULL,
  `coordinates` varchar(255) NOT NULL,
  `population` int NOT NULL,
  PRIMARY KEY (`barangay_id`)
) ENGINE=InnoDB AUTO_INCREMENT=25 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `barangays`
--

LOCK TABLES `barangays` WRITE;
/*!40000 ALTER TABLE `barangays` DISABLE KEYS */;
INSERT INTO `barangays` VALUES (1,'Abuanan','Bago City','10.5254,122.9915',0),(2,'Alianza','Bago City','10.4734,122.9301',0),(3,'Atipuluan','Bago City','10.5109,122.9564',0),(4,'Bacong-Montilla','Bago City','10.519,123.0351',0),(5,'Bagroy','Bago City','10.4761,122.8738',0),(6,'Balingasag','Bago City','10.5309,122.844',0),(7,'Binubuhan','Bago City','10.4566,123.0083',0),(8,'Busay','Bago City','10.5372,122.8847',0),(9,'Calumangan','Bago City','10.5598,122.8765',0),(10,'Caridad','Bago City','10.4812,122.9084',0),(11,'Don Jorge Araneta','Bago City','10.4765,122.9466',0),(12,'Dulao','Bago City','10.5482,122.9537',0),(13,'Ilijan','Bago City','10.4526,123.0553',0),(14,'Lag-asan','Bago City','10.5233,122.8395',0),(15,'Ma-ao','Bago City','10.4896,122.9897',0),(16,'Mailum','Bago City','10.4618,123.0493',0),(17,'Malingin','Bago City','10.4933,122.9175',0),(18,'Napoles','Bago City','10.5128,122.898',0),(19,'Pacol','Bago City','10.4953,122.8672',0),(20,'Poblacion','Bago City','10.5381,122.8359',0),(21,'Sagasa','Bago City','10.4709,122.8924',0),(22,'Sampinit','Bago City','10.5428,122.8515',0),(23,'Tabunan','Bago City','10.5739,122.9393',0),(24,'Taloc','Bago City','10.5716,122.9119',0);
/*!40000 ALTER TABLE `barangays` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `bhw`
--

DROP TABLE IF EXISTS `bhw`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `bhw` (
  `bhw_id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `password` varchar(255) NOT NULL,
  `email` varchar(254) NOT NULL,
  `contact_info` varchar(100) NOT NULL,
  `barangay_id` int NOT NULL,
  PRIMARY KEY (`bhw_id`),
  UNIQUE KEY `email` (`email`),
  KEY `bhw_barangay_id_8faa8923_fk_barangays_barangay_id` (`barangay_id`),
  CONSTRAINT `bhw_barangay_id_8faa8923_fk_barangays_barangay_id` FOREIGN KEY (`barangay_id`) REFERENCES `barangays` (`barangay_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `bhw`
--

LOCK TABLES `bhw` WRITE;
/*!40000 ALTER TABLE `bhw` DISABLE KEYS */;
/*!40000 ALTER TABLE `bhw` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `disease_category_thresholds`
--

DROP TABLE IF EXISTS `disease_category_thresholds`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `disease_category_thresholds` (
  `id` int NOT NULL AUTO_INCREMENT,
  `category_level` varchar(32) NOT NULL,
  `warning_threshold` smallint unsigned NOT NULL,
  `outbreak_threshold` smallint unsigned NOT NULL,
  `time_window_days` smallint unsigned NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `category_level` (`category_level`),
  CONSTRAINT `disease_category_thresholds_chk_1` CHECK ((`warning_threshold` >= 0)),
  CONSTRAINT `disease_category_thresholds_chk_2` CHECK ((`outbreak_threshold` >= 0)),
  CONSTRAINT `disease_category_thresholds_chk_3` CHECK ((`time_window_days` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `disease_category_thresholds`
--

LOCK TABLES `disease_category_thresholds` WRITE;
/*!40000 ALTER TABLE `disease_category_thresholds` DISABLE KEYS */;
INSERT INTO `disease_category_thresholds` VALUES (1,'Category 1',1,1,7,1),(2,'Category 2',2,3,7,1);
/*!40000 ALTER TABLE `disease_category_thresholds` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_admin_log`
--

DROP TABLE IF EXISTS `django_admin_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_admin_log` (
  `id` int NOT NULL AUTO_INCREMENT,
  `action_time` datetime(6) NOT NULL,
  `object_id` longtext,
  `object_repr` varchar(200) NOT NULL,
  `action_flag` smallint unsigned NOT NULL,
  `change_message` longtext NOT NULL,
  `content_type_id` int DEFAULT NULL,
  `user_id` int NOT NULL,
  PRIMARY KEY (`id`),
  KEY `django_admin_log_content_type_id_c4bce8eb_fk_django_co` (`content_type_id`),
  KEY `django_admin_log_user_id_c564eba6_fk_auth_user_id` (`user_id`),
  CONSTRAINT `django_admin_log_content_type_id_c4bce8eb_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`),
  CONSTRAINT `django_admin_log_user_id_c564eba6_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`),
  CONSTRAINT `django_admin_log_chk_1` CHECK ((`action_flag` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_admin_log`
--

LOCK TABLES `django_admin_log` WRITE;
/*!40000 ALTER TABLE `django_admin_log` DISABLE KEYS */;
/*!40000 ALTER TABLE `django_admin_log` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_content_type`
--

DROP TABLE IF EXISTS `django_content_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_content_type` (
  `id` int NOT NULL AUTO_INCREMENT,
  `app_label` varchar(100) NOT NULL,
  `model` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `django_content_type_app_label_model_76bd3d3b_uniq` (`app_label`,`model`)
) ENGINE=InnoDB AUTO_INCREMENT=41 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_content_type`
--

LOCK TABLES `django_content_type` WRITE;
/*!40000 ALTER TABLE `django_content_type` DISABLE KEYS */;
INSERT INTO `django_content_type` VALUES (1,'admin','logentry'),(2,'auth','group'),(3,'auth','permission'),(4,'auth','user'),(5,'contenttypes','contenttype'),(7,'myapp','admin'),(20,'myapp','alert'),(8,'myapp','alerts'),(21,'myapp','auditlog'),(22,'myapp','barangay'),(37,'myapp','barangayepidemicstatus'),(9,'myapp','barangays'),(10,'myapp','bhw'),(38,'myapp','diseasecategorythreshold'),(23,'myapp','environmentaldata'),(11,'myapp','environmentdata'),(12,'myapp','healthreport'),(13,'myapp','historicalrecords'),(14,'myapp','incidentreport'),(24,'myapp','loginattempt'),(36,'myapp','mitigationprotocol'),(15,'myapp','mlaipredictions'),(16,'myapp','notification'),(25,'myapp','notificationlog'),(26,'myapp','ocrresult'),(39,'myapp','outbreakthresholdlog'),(33,'myapp','patientcase'),(17,'myapp','patients'),(32,'myapp','pulsesession'),(27,'myapp','registrationrequest'),(18,'myapp','riskanalysis'),(28,'myapp','riskassessment'),(19,'myapp','superadmin'),(29,'myapp','surveillancereport'),(34,'myapp','surveillancesession'),(35,'myapp','symptom'),(30,'myapp','systemlog'),(31,'myapp','user'),(40,'reports','barangayrisklog'),(6,'sessions','session');
/*!40000 ALTER TABLE `django_content_type` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_migrations`
--

DROP TABLE IF EXISTS `django_migrations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_migrations` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `app` varchar(255) NOT NULL,
  `name` varchar(255) NOT NULL,
  `applied` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=33 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_migrations`
--

LOCK TABLES `django_migrations` WRITE;
/*!40000 ALTER TABLE `django_migrations` DISABLE KEYS */;
INSERT INTO `django_migrations` VALUES (1,'contenttypes','0001_initial','2026-06-05 15:24:26.846797'),(2,'auth','0001_initial','2026-06-05 15:24:27.888319'),(3,'admin','0001_initial','2026-06-05 15:24:28.138126'),(4,'admin','0002_logentry_remove_auto_add','2026-06-05 15:24:28.150020'),(5,'admin','0003_logentry_add_action_flag_choices','2026-06-05 15:24:28.164088'),(6,'contenttypes','0002_remove_content_type_name','2026-06-05 15:24:28.384820'),(7,'auth','0002_alter_permission_name_max_length','2026-06-05 15:24:28.506109'),(8,'auth','0003_alter_user_email_max_length','2026-06-05 15:24:28.561946'),(9,'auth','0004_alter_user_username_opts','2026-06-05 15:24:28.577717'),(10,'auth','0005_alter_user_last_login_null','2026-06-05 15:24:28.685716'),(11,'auth','0006_require_contenttypes_0002','2026-06-05 15:24:28.689676'),(12,'auth','0007_alter_validators_add_error_messages','2026-06-05 15:24:28.700459'),(13,'auth','0008_alter_user_username_max_length','2026-06-05 15:24:28.820828'),(14,'auth','0009_alter_user_last_name_max_length','2026-06-05 15:24:28.939803'),(15,'auth','0010_alter_group_name_max_length','2026-06-05 15:24:28.975480'),(16,'auth','0011_update_proxy_permissions','2026-06-05 15:24:28.992200'),(17,'auth','0012_alter_user_first_name_max_length','2026-06-05 15:24:29.108706'),(19,'sessions','0001_initial','2026-06-05 15:24:30.829343'),(20,'myapp','0001_initial','2026-06-10 15:47:28.209892'),(21,'myapp','0002_add_pulse_session','2026-06-10 15:47:28.215184'),(22,'myapp','0003_surveillance_report_patient_id','2026-06-12 14:15:39.074129'),(23,'myapp','0004_surveillancereport_status','2026-06-13 13:18:57.223314'),(24,'myapp','0005_batch_entry_models','2026-06-13 14:30:18.709522'),(25,'myapp','0006_patientcase_age_sex','2026-06-13 14:58:35.894651'),(26,'myapp','0007_symptom_model','2026-06-21 13:25:28.410643'),(27,'myapp','0008_mitigationprotocol','2026-06-21 13:49:51.089964'),(28,'myapp','0009_surveillancereport_ml_flags','2026-06-21 14:13:40.370054'),(29,'myapp','0010_disease_category_thresholds','2026-06-21 14:40:24.993877'),(30,'myapp','0011_log_display_names','2026-06-21 15:36:50.768870'),(31,'myapp','0012_patient_demographics','2026-06-22 14:49:31.664304'),(32,'reports','0001_barangay_risk_log','2026-06-23 14:12:35.390973');
/*!40000 ALTER TABLE `django_migrations` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_session`
--

DROP TABLE IF EXISTS `django_session`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_session` (
  `session_key` varchar(40) NOT NULL,
  `session_data` longtext NOT NULL,
  `expire_date` datetime(6) NOT NULL,
  PRIMARY KEY (`session_key`),
  KEY `django_session_expire_date_a5c62663` (`expire_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_session`
--

LOCK TABLES `django_session` WRITE;
/*!40000 ALTER TABLE `django_session` DISABLE KEYS */;
INSERT INTO `django_session` VALUES ('3maqvnfmidxgydryu6wtzy0od2xf8ixi','.eJw9jMEKwjAQRH-l5FwEES89iUdB8A_Cpm7TJZtuiVs0iP9uEsHb8N7MvM32wGTpboZ9_8uaVzRDy6Y308ZsF4gVXSAHStpduzMqKRSNEYiLcg2Ew_HkK9mNEotNwnXnIMHiIdsZgXW2T0mhna9JJmK0FMHXYkH_ruJLC7qJYxhJFvP5AtSNO2A:1wc1NC:KXnpiWvhYSlRpzD60cbUTxnGENsvx9ApUiQiU2vaGKc','2026-06-23 15:41:06.749592'),('3rhn6bx39dfbtowita217sroe5mn6oqb','.eJw9jDEOwjAMRa-CPFcdGDvBysweueCmUZ2kch1Bhbg7cZC6WM_vf_sDZSNx4QnDufuz7ivB0Bg6mAqzSxhN3WnTk9podJO-Fihi4Bqav3hb-keONZDMdjSiYPK4u5mQdXavLEv7vEqeApMLEb0Vqzq6Sm-t6joWTJjg-wOxgTl6:1wckqb:4chGrslfhTmn1YrOahgAGlvmwfnkc9Jq7KuRjJ-_lHo','2026-06-25 16:14:29.010339'),('6pheet4saiszyhywf8ylpvj1ylt71d2k','.eJw9jMEKwjAQRH-l5FwEES89iUdB8A_Cpm7TJZtuiVs0iP9uEsHb8N7MvM32wGTpboZ9_8uaVzRDy6Y308ZsF4gVXSAHStpduzMqKRSNEYiLcg2Ew_HkK9mNEotNwnXnIMHiIdsZgXW2T0mhna9JJmK0FMHXYkH_ruJLC7qJYxhJFvP5AtSNO2A:1wYOlx:uFOcfdtvJDs4dnBkWOanajcTjQV8jZbm80XsgvlU8-M','2026-06-13 15:51:41.794021'),('7wxvejjc0yk41uqh094qngz3y6aeulns','.eJxNzEsKAjEMgOGrSNaD4HZWegYPUKLNlED6IE3BIt59WoYBd-H7k3yhVVLHHtbbcszWC8EK6CMnWGBrIi5hnPbs1SheHjNxNUXLOlYoIst5ci9NKl0lv1FG0yz_34rmjYUcRwzTB71QMQXszuhjB2GtHBJ5d7bJvx0C5zrT:1wfJIl:m3MhHAvdogZpucJ_DdSAA7eoeIdVLsnfYpoRVn8i2Vs','2026-07-02 17:26:07.926494'),('9aijkla6j24acbauqkmbb5pry46f9gwu','.eJxNjEEKwzAMBL9SdA6FXnNq35AHGLVRgkCyjSxDTenfY1MKuS0zu_uBWsgCrzDfpl_2lglmwFU5wgRbFQkRdbClFSe9PIbi4oaerFdIkeU_uecqha6SXijdWZLzW7a0sVBgxX3wjp5oGHdswentA30PD1ky8w:1wcHnt:IgEzuspGjWsI8YGFkoVdjwRVOQ5fiusb-rW2CRNhL8Q','2026-06-24 09:13:45.249516'),('cu2b3057wiw928qt262127su8adolj26','.eJwljLEOwjAMRH-lylwxILF0gpWVD4hMcCJXTlK5CWqE-HfisJ3eu7uPqTuKpZdZLvM_l7ahWUY2s_GV2SaIiu7ILU2P6VZXlNwlRiDuYlUBg56vQeHJ5dgLklmHe5U3EjMkhzZ7T258b5I9MVqKELTW0RMEUoBmCx5F0fcHs743yQ:1wcPMN:faF36I91O7Kp2uFkj4LjH-UYXZBRwuheFVxb3BbvAAY','2026-06-24 17:17:51.560794'),('h7yawqpanvpv13gvti255hn9v59hb139','.eJxNjEEKwzAMBL9SdA6FXnNq35AHGLVRgkCyjSxDTenfY1MKuS0zu_uBWsgCrzDfpl_2lglmwFU5wgRbFQkRdbClFSe9PIbi4oaerFdIkeU_uecqha6SXijdWZLzW7a0sVBgxX3wjp5oGHdswentA30PD1ky8w:1weaIX:FGuGO2apP_eDEUjsu59H7XUKCMYRwGaaZOdc8_4VtV0','2026-06-30 17:22:53.725400'),('hbc0vrit888yttko6dglrtit3tlah6bi','.eJw9jMEKwjAQRH-l5FwEES89iUdB8A_Cpm7TJZtuiVs0iP9uEsHb8N7MvM32wGTpboZ9_8uaVzRDy6Y308ZsF4gVXSAHStpduzMqKRSNEYiLcg2Ew_HkK9mNEotNwnXnIMHiIdsZgXW2T0mhna9JJmK0FMHXYkH_ruJLC7qJYxhJFvP5AtSNO2A:1wbg3q:QwKwG3EObCUHzL26EcNcuJwvUe5GoSaHMDO2RPH3ryo','2026-06-22 16:55:42.581432'),('n43pvywy0g3cssc5akq25qza6457kkmz','.eJxNjEEKwzAMBL9SdA6FXnNq35AHGLVRgkCyjSxDTenfY1MKuS0zu_uBWsgCrzDfpl_2lglmwFU5wgRbFQkRdbClFSe9PIbi4oaerFdIkeU_uecqha6SXijdWZLzW7a0sVBgxX3wjp5oGHdswentA30PD1ky8w:1weF23:Ctq9rnK4lK8WkTPkYYd9J6Dmn0vi_of-74GXTkVOcOk','2026-06-29 18:40:27.360602'),('rz22cbruzx3h28bh16ss10q3zh0bzuiw','.eJxNjEEKwzAMBL9SdA6FXnNq35AHGLVRgkCyjSxDTenfY1MKuS0zu_uBWsgCrzDfpl_2lglmwFU5wgRbFQkRdbClFSe9PIbi4oaerFdIkeU_uecqha6SXijdWZLzW7a0sVBgxX3wjp5oGHdswentA30PD1ky8w:1weEZA:Wvk1KYDYlKLqK5Z8qVCM9xNCSRv2K4uaXSz_Wh4Jgt8','2026-06-29 18:10:36.035843'),('ta9b0i0hm3x848xfy6rzy6bo2sctcdyp','eyJ1c2VyX2lkIjoxLCJyb2xlIjoiYWRtaW4ifQ:1wc2DD:C1wGb_1uK-oPcwCuhif5t8QPWjuOhZpkB9aixW_xfwY','2026-06-23 16:34:51.763151'),('uq9yjtqbp7mz47woksc8qi179x4rngep','.eJxNjEEKwzAMBL9SdA6FXnNq35AHGLVRgkCyjSxDTenfY1MKuS0zu_uBWsgCrzDfpl_2lglmwFU5wgRbFQkRdbClFSe9PIbi4oaerFdIkeU_uecqha6SXijdWZLzW7a0sVBgxX3wjp5oGHdswentA30PD1ky8w:1wbv9m:Imgr72PsijOLTxPE51ytgtzBwtncAN_-0KbeynNlfoE','2026-06-23 09:02:50.224138'),('uyxybgbctg4v597njdoypyx3p05y4vfc','.eJxNjEEKwzAMBL9SdA6FXnNq35AHGLVRgkCyjSxDTenfY1MKuS0zu_uBWsgCrzDfpl_2lglmwFU5wgRbFQkRdbClFSe9PIbi4oaerFdIkeU_uecqha6SXijdWZLzW7a0sVBgxX3wjp5oGHdswentA30PD1ky8w:1waTYL:ou3yH8QWcRXAQdpW1oF8SzpoVtseQ21dPrXQOQWrjdc','2026-06-19 09:22:13.156192'),('vagndouo9odniwgwzbv5jfgshjf1mmgs','.eJw9jMEKwjAQRH-l5FwEES89iUdB8A_Cpm7TJZtuiVs0iP9uEsHb8N7MvM32wGTpboZ9_8uaVzRDy6Y308ZsF4gVXSAHStpduzMqKRSNEYiLcg2Ew_HkK9mNEotNwnXnIMHiIdsZgXW2T0mhna9JJmK0FMHXYkH_ruJLC7qJYxhJFvP5AtSNO2A:1wdLnT:1Ypxvlq9DL5dC_J-9hh9ZpLk-XPuCCcMA_P7Oc2PdWQ','2026-06-27 07:41:43.401852'),('wvwybluwvx5l8oxhhy3jx8enevuqhcl8','.eJxNjEEKwzAMBL9SdA6FXnNq35AHGLVRgkCyjSxDTenfY1MKuS0zu_uBWsgCrzDfpl_2lglmwFU5wgRbFQkRdbClFSe9PIbi4oaerFdIkeU_uecqha6SXijdWZLzW7a0sVBgxX3wjp5oGHdswentA30PD1ky8w:1wYmAO:2aZ_BvgvvrDM8FOQYO7trOba7A3rLeTrjx7oHPhKbOE','2026-06-14 16:50:28.863927'),('xgpfl7tlqpwtmz1i3a2ox7dr8rvicc2z','.eJxNjEEKwzAMBL9SdA6FXnNq35AHGLVRgkCyjSxDTenfY1MKuS0zu_uBWsgCrzDfpl_2lglmwFU5wgRbFQkRdbClFSe9PIbi4oaerFdIkeU_uecqha6SXijdWZLzW7a0sVBgxX3wjp5oGHdswentA30PD1ky8w:1wbKUa:QUlMW9jD0GtZEhJuiR98ta5KI7TwQx-QwOjumYiqmTc','2026-06-21 17:53:52.170880'),('xj1wxy6iu1hctmgqsehe9r1kxsrkvr0s','.eJxNjEEKwzAMBL9SdA6FXnNq35AHGLVRgkCyjSxDTenfY1MKuS0zu_uBWsgCrzDfpl_2lglmwFU5wgRbFQkRdbClFSe9PIbi4oaerFdIkeU_uecqha6SXijdWZLzW7a0sVBgxX3wjp5oGHdswentA30PD1ky8w:1weEUc:FSIJ1sII-cHptdS-TgPKn2YfqBgmAiqP5fKZ-swcbZE','2026-06-29 18:05:54.188468');
/*!40000 ALTER TABLE `django_session` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `environment_data`
--

DROP TABLE IF EXISTS `environment_data`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `environment_data` (
  `environment_id` int NOT NULL AUTO_INCREMENT,
  `temperature` decimal(5,2) NOT NULL,
  `humidity` decimal(5,2) NOT NULL,
  `weather_condition` varchar(100) NOT NULL,
  `recorded_date` datetime(6) NOT NULL,
  `barangay_id` int NOT NULL,
  PRIMARY KEY (`environment_id`),
  KEY `environment_data_barangay_id_bcad2ffd_fk_barangays_barangay_id` (`barangay_id`),
  CONSTRAINT `environment_data_barangay_id_bcad2ffd_fk_barangays_barangay_id` FOREIGN KEY (`barangay_id`) REFERENCES `barangays` (`barangay_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `environment_data`
--

LOCK TABLES `environment_data` WRITE;
/*!40000 ALTER TABLE `environment_data` DISABLE KEYS */;
/*!40000 ALTER TABLE `environment_data` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `environmental_data`
--

DROP TABLE IF EXISTS `environmental_data`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `environmental_data` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `barangay_id` bigint NOT NULL,
  `data_source` varchar(150) DEFAULT NULL,
  `temperature` decimal(5,2) DEFAULT NULL,
  `humidity` decimal(5,2) DEFAULT NULL,
  `rainfall` decimal(7,2) DEFAULT NULL,
  `air_quality_index` decimal(6,2) DEFAULT NULL,
  `recorded_at` datetime(6) NOT NULL,
  `risk_factor_note` longtext,
  `created_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `environmental_data`
--

LOCK TABLES `environmental_data` WRITE;
/*!40000 ALTER TABLE `environmental_data` DISABLE KEYS */;
INSERT INTO `environmental_data` VALUES (1,20,'open-meteo-bago-city',25.50,90.00,0.60,NULL,'2026-06-22 14:06:43.505102','Open-Meteo snapshot for Bago City (10.5383, 122.8414). Temperature 25.5°C, humidity 90.0%. Elevated vector-breeding risk: active precipitation may expand mosquito habitat.','2026-06-22 14:06:43.505102'),(2,20,'open-meteo-bago-city',25.60,91.00,0.80,NULL,'2026-06-22 14:48:36.447161','Open-Meteo snapshot for Bago City (10.5383, 122.8414). Temperature 25.6°C, humidity 91.0%. Elevated vector-breeding risk: active precipitation may expand mosquito habitat.','2026-06-22 14:48:36.447161'),(3,20,'open-meteo-bago-city',27.60,83.00,0.20,NULL,'2026-06-23 06:50:25.765176','Open-Meteo snapshot for Bago City (10.5383, 122.8414). Temperature 27.6°C, humidity 83.0%. Elevated vector-breeding risk: active precipitation may expand mosquito habitat.','2026-06-23 06:50:25.765176'),(4,20,'open-meteo-bago-city',25.90,90.00,0.40,NULL,'2026-06-23 13:41:09.999925','Open-Meteo snapshot for Bago City (10.5383, 122.8414). Temperature 25.9°C, humidity 90.0%. Elevated vector-breeding risk: active precipitation may expand mosquito habitat.','2026-06-23 13:41:09.999925'),(5,20,'open-meteo-bago-city',28.90,78.00,0.00,NULL,'2026-06-24 07:13:48.396415','Open-Meteo snapshot for Bago City (10.5383, 122.8414). Temperature 28.9°C, humidity 78.0%.','2026-06-24 07:13:48.396415'),(6,20,'open-meteo-bago-city',28.30,78.00,0.00,NULL,'2026-06-24 14:11:54.401438','Open-Meteo snapshot for Bago City (10.5383, 122.8414). Temperature 28.3°C, humidity 78.0%.','2026-06-24 14:11:54.401438'),(7,20,'open-meteo-bago-city',28.40,76.00,0.00,NULL,'2026-06-24 15:01:19.257996','Open-Meteo snapshot for Bago City (10.5383, 122.8414). Temperature 28.4°C, humidity 76.0%.','2026-06-24 15:01:19.257996'),(8,20,'open-meteo-bago-city',26.50,92.00,0.00,NULL,'2026-06-25 13:53:48.763913','Open-Meteo snapshot for Bago City (10.5383, 122.8414). Temperature 26.5°C, humidity 92.0%.','2026-06-25 13:53:48.763913'),(9,20,'open-meteo-bago-city',29.00,80.00,0.10,NULL,'2026-06-27 05:41:45.673536','Open-Meteo snapshot for Bago City (10.5383, 122.8414). Temperature 29.0°C, humidity 80.0%. Elevated vector-breeding risk: active precipitation may expand mosquito habitat.','2026-06-27 05:41:45.673536'),(10,20,'open-meteo-bago-city',24.60,95.00,0.00,NULL,'2026-06-29 16:05:55.904379','Open-Meteo snapshot for Bago City (10.5383, 122.8414). Temperature 24.6°C, humidity 95.0%.','2026-06-29 16:05:55.904379'),(11,20,'open-meteo-bago-city',24.70,95.00,0.00,NULL,'2026-06-29 16:40:28.921501','Open-Meteo snapshot for Bago City (10.5383, 122.8414). Temperature 24.7°C, humidity 95.0%.','2026-06-29 16:40:28.921501'),(12,20,'open-meteo-bago-city',26.80,85.00,0.00,NULL,'2026-06-30 15:22:55.607213','Open-Meteo snapshot for Bago City (10.5383, 122.8414). Temperature 26.8°C, humidity 85.0%.','2026-06-30 15:22:55.607213'),(13,20,'open-meteo-bago-city',26.40,93.00,0.00,NULL,'2026-07-01 12:45:52.751435','Open-Meteo snapshot for Bago City (10.5383, 122.8414). Temperature 26.4°C, humidity 93.0%.','2026-07-01 12:45:52.751435'),(14,20,'open-meteo-bago-city',26.90,92.00,0.00,NULL,'2026-07-02 14:54:04.982786','Open-Meteo snapshot for Bago City (10.5383, 122.8414). Temperature 26.9°C, humidity 92.0%.','2026-07-02 14:54:04.982786'),(15,20,'open-meteo-bago-city',26.80,93.00,0.00,NULL,'2026-07-02 15:26:09.403341','Open-Meteo snapshot for Bago City (10.5383, 122.8414). Temperature 26.8°C, humidity 93.0%.','2026-07-02 15:26:09.403341');
/*!40000 ALTER TABLE `environmental_data` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `health_report`
--

DROP TABLE IF EXISTS `health_report`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `health_report` (
  `report_id` int NOT NULL AUTO_INCREMENT,
  `symptoms` longtext NOT NULL,
  `severity_level` varchar(50) NOT NULL,
  `report_date` datetime(6) NOT NULL,
  `admin_id` int DEFAULT NULL,
  `barangay_id` int NOT NULL,
  `bhw_id` int NOT NULL,
  PRIMARY KEY (`report_id`),
  KEY `health_report_admin_id_c6b4fe8b_fk_admin_admin_id` (`admin_id`),
  KEY `health_report_barangay_id_c1c0228b_fk_barangays_barangay_id` (`barangay_id`),
  KEY `health_report_bhw_id_0d7da41c_fk_bhw_bhw_id` (`bhw_id`),
  CONSTRAINT `health_report_admin_id_c6b4fe8b_fk_admin_admin_id` FOREIGN KEY (`admin_id`) REFERENCES `admin` (`admin_id`),
  CONSTRAINT `health_report_barangay_id_c1c0228b_fk_barangays_barangay_id` FOREIGN KEY (`barangay_id`) REFERENCES `barangays` (`barangay_id`),
  CONSTRAINT `health_report_bhw_id_0d7da41c_fk_bhw_bhw_id` FOREIGN KEY (`bhw_id`) REFERENCES `bhw` (`bhw_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `health_report`
--

LOCK TABLES `health_report` WRITE;
/*!40000 ALTER TABLE `health_report` DISABLE KEYS */;
/*!40000 ALTER TABLE `health_report` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `historical_records`
--

DROP TABLE IF EXISTS `historical_records`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `historical_records` (
  `record_id` int NOT NULL AUTO_INCREMENT,
  `disease_type` varchar(100) NOT NULL,
  `case_status` varchar(50) NOT NULL,
  `treatment_status` varchar(100) NOT NULL,
  `date_recorded` date NOT NULL,
  `notes` longtext,
  `incident_id` int NOT NULL,
  `patient_id` int NOT NULL,
  PRIMARY KEY (`record_id`),
  KEY `historical_records_incident_id_c00abc1b_fk_incident_` (`incident_id`),
  KEY `historical_records_patient_id_80147cc0_fk_patients_patient_id` (`patient_id`),
  CONSTRAINT `historical_records_incident_id_c00abc1b_fk_incident_` FOREIGN KEY (`incident_id`) REFERENCES `incident_report` (`incident_id`),
  CONSTRAINT `historical_records_patient_id_80147cc0_fk_patients_patient_id` FOREIGN KEY (`patient_id`) REFERENCES `patients` (`patient_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `historical_records`
--

LOCK TABLES `historical_records` WRITE;
/*!40000 ALTER TABLE `historical_records` DISABLE KEYS */;
/*!40000 ALTER TABLE `historical_records` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `incident_report`
--

DROP TABLE IF EXISTS `incident_report`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `incident_report` (
  `incident_id` int NOT NULL AUTO_INCREMENT,
  `disease_type` varchar(100) NOT NULL,
  `case_count` int NOT NULL,
  `incident_date` date NOT NULL,
  `response_action` longtext NOT NULL,
  `report_id` int NOT NULL,
  `patient_id` int NOT NULL,
  PRIMARY KEY (`incident_id`),
  KEY `incident_report_report_id_ea62b835_fk_health_report_report_id` (`report_id`),
  KEY `incident_report_patient_id_2041a4c5_fk_patients_patient_id` (`patient_id`),
  CONSTRAINT `incident_report_patient_id_2041a4c5_fk_patients_patient_id` FOREIGN KEY (`patient_id`) REFERENCES `patients` (`patient_id`),
  CONSTRAINT `incident_report_report_id_ea62b835_fk_health_report_report_id` FOREIGN KEY (`report_id`) REFERENCES `health_report` (`report_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `incident_report`
--

LOCK TABLES `incident_report` WRITE;
/*!40000 ALTER TABLE `incident_report` DISABLE KEYS */;
/*!40000 ALTER TABLE `incident_report` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `login_attempts`
--

DROP TABLE IF EXISTS `login_attempts`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `login_attempts` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `email` varchar(255) NOT NULL,
  `attempted_at` datetime(6) NOT NULL,
  `success` tinyint(1) NOT NULL,
  `ip_address` varchar(45) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=93 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `login_attempts`
--

LOCK TABLES `login_attempts` WRITE;
/*!40000 ALTER TABLE `login_attempts` DISABLE KEYS */;
INSERT INTO `login_attempts` VALUES (1,'admin@pulse.local','2026-06-10 15:51:25.562284',1,'127.0.0.1'),(2,'admin@pulse.local','2026-06-13 13:21:03.316635',1,'127.0.0.1'),(3,'betitak35@gmail.com','2026-06-13 13:21:58.377080',1,'127.0.0.1'),(4,'admin@pulse.local','2026-06-13 13:23:38.021887',1,'127.0.0.1'),(5,'betitak35@gmail.com','2026-06-13 13:51:41.776861',1,'127.0.0.1'),(6,'admin@pulse.local','2026-06-14 14:39:32.462597',1,'127.0.0.1'),(7,'admin@pulse.local','2026-06-14 14:50:28.842891',1,'127.0.0.1'),(8,'admin@pulse.local','2026-06-15 06:27:46.407474',1,'127.0.0.1'),(9,'betitak35@gmail.com','2026-06-15 06:28:03.633470',1,'127.0.0.1'),(10,'admin@pulse.local','2026-06-15 07:12:52.674148',1,'127.0.0.1'),(11,'betitak35@gmail.com','2026-06-15 07:29:04.534618',1,'127.0.0.1'),(16,'admin@pulse.local','2026-06-16 19:05:13.876213',1,'127.0.0.1'),(17,'admin@pulse.local','2026-06-16 19:55:27.359703',1,'127.0.0.1'),(19,'test@gmail.com','2026-06-16 19:57:04.743893',1,'127.0.0.1'),(20,'admin@pulse.local','2026-06-19 06:43:33.680300',1,'127.0.0.1'),(21,'betitak35@gmail.com','2026-06-19 07:10:58.854865',1,'127.0.0.1'),(22,'admin@pulse.local','2026-06-19 07:21:38.415919',1,'127.0.0.1'),(23,'admin@pulse.local','2026-06-19 07:22:13.137192',1,'127.0.0.1'),(24,'admin@pulse.local','2026-06-21 13:42:25.707826',1,'127.0.0.1'),(25,'betitak35@gmail.com','2026-06-21 15:17:46.078638',1,'127.0.0.1'),(26,'admin@pulse.local','2026-06-21 15:22:56.008572',1,'127.0.0.1'),(27,'betitak35@gmail.com','2026-06-21 15:43:03.530856',1,'127.0.0.1'),(28,'admin@pulse.local','2026-06-21 15:43:13.738467',1,'127.0.0.1'),(29,'betitak35@gmail.com','2026-06-21 15:43:34.563000',1,'127.0.0.1'),(30,'admin@pulse.local','2026-06-21 15:45:25.822554',1,'127.0.0.1'),(31,'betitak35@gmail.com','2026-06-21 15:51:03.798013',1,'127.0.0.1'),(32,'admin@pulse.local','2026-06-21 15:53:52.157233',1,'127.0.0.1'),(33,'admin@pulse.local','2026-06-22 13:43:20.628301',1,'127.0.0.1'),(34,'betitak35@gmail.com','2026-06-22 13:46:00.904634',1,'127.0.0.1'),(35,'betitak35@gmail.com','2026-06-22 14:35:02.751402',1,'127.0.0.1'),(37,'superadmin@pulse.local','2026-06-22 14:48:35.026618',1,'127.0.0.1'),(38,'betitak35@gmail.com','2026-06-22 14:55:42.561405',1,'127.0.0.1'),(40,'admin@pulse.local','2026-06-23 06:50:24.556090',1,'127.0.0.1'),(41,'betitak35@gmail.com','2026-06-23 07:01:24.929090',1,'127.0.0.1'),(42,'admin@pulse.local','2026-06-23 07:02:50.204099',1,'127.0.0.1'),(43,'betitak35@gmail.com','2026-06-23 13:41:06.725611',1,'127.0.0.1'),(44,'admin@pulse.local','2026-06-24 07:13:45.206775',1,'127.0.0.1'),(45,'betitak35@gmail.com','2026-06-24 14:11:52.458032',1,'127.0.0.1'),(46,'admin@pulse.local','2026-06-24 15:01:17.770748',1,'127.0.0.1'),(49,'admin@pulse.local','2026-06-24 15:03:40.033160',1,'127.0.0.1'),(51,'admin@pulse.local','2026-06-24 15:04:36.363443',1,'127.0.0.1'),(52,'jojowowers@gmail.com','2026-06-24 15:06:13.947615',1,'127.0.0.1'),(53,'admin@pulse.local','2026-06-24 15:15:44.521223',1,'127.0.0.1'),(55,'admin@pulse.local','2026-06-24 15:16:49.052095',1,'127.0.0.1'),(56,'jelynaujero2@gmail.com','2026-06-24 15:17:40.551702',1,'127.0.0.1'),(58,'admin@pulse.local','2026-06-25 13:53:46.990105',1,'127.0.0.1'),(61,'test@gmail.com','2026-06-25 14:14:28.993280',1,'127.0.0.1'),(62,'betitak35@gmail.com','2026-06-27 05:41:43.352299',1,'127.0.0.1'),(73,'admin@pulse.local','2026-06-29 16:05:54.165482',1,'127.0.0.1'),(74,'admin@pulse.local','2026-06-29 16:10:36.015845',1,'127.0.0.1'),(75,'admin@pulse.local','2026-06-29 16:40:27.344852',1,'127.0.0.1'),(76,'admin@pulse.local','2026-06-30 15:22:53.703125',1,'127.0.0.1'),(77,'admin@pulse.local','2026-07-01 12:45:50.977705',1,'127.0.0.1'),(78,'admin@pulse.local','2026-07-02 14:54:03.189257',1,'127.0.0.1'),(79,'test123@gmail.com','2026-07-02 14:55:43.371113',1,'127.0.0.1'),(80,'test123@gmail.com','2026-07-02 15:10:32.021781',0,'127.0.0.1'),(81,'test123@gmail.com','2026-07-02 15:10:36.759937',1,'127.0.0.1'),(82,'admin@pulse.local','2026-07-02 15:15:26.075642',1,'127.0.0.1'),(83,'admin@pulse.local','2026-07-02 15:15:27.681438',1,'127.0.0.1'),(84,'testjr123@gmail.com','2026-07-02 15:19:07.143499',1,'127.0.0.1'),(85,'testjr123@gmail.com','2026-07-02 15:20:11.030426',0,'127.0.0.1'),(86,'testjr123@gmail.com','2026-07-02 15:20:16.561388',0,'127.0.0.1'),(87,'testjr123@gmail.com','2026-07-02 15:20:22.975070',1,'127.0.0.1'),(88,'admin@pulse.local','2026-07-02 15:22:43.773171',1,'127.0.0.1'),(89,'testjr123@gmail.com','2026-07-02 15:25:41.855389',0,'127.0.0.1'),(90,'testjr123@gmail.com','2026-07-02 15:25:56.727738',0,'127.0.0.1'),(91,'testjr123@gmail.com','2026-07-02 15:26:02.117676',0,'127.0.0.1'),(92,'admin@pulse.local','2026-07-02 15:26:07.914447',1,'127.0.0.1');
/*!40000 ALTER TABLE `login_attempts` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `mitigation_protocols`
--

DROP TABLE IF EXISTS `mitigation_protocols`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `mitigation_protocols` (
  `id` int NOT NULL AUTO_INCREMENT,
  `disease_label` varchar(150) NOT NULL,
  `action_text` longtext NOT NULL,
  `priority` varchar(10) NOT NULL,
  `action_category` varchar(20) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `sort_order` smallint unsigned NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_mitigation_disease_sort` (`disease_label`,`sort_order`),
  CONSTRAINT `mitigation_protocols_chk_1` CHECK ((`sort_order` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=19 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `mitigation_protocols`
--

LOCK TABLES `mitigation_protocols` WRITE;
/*!40000 ALTER TABLE `mitigation_protocols` DISABLE KEYS */;
INSERT INTO `mitigation_protocols` VALUES (1,'Dengue','Clear stagnant standing water containers and cut down long weeds acting as mosquito resting sites.','high','environmental',1,1),(2,'Dengue','Apply safe larvicides to permanent community water storage setups.','medium','environmental',1,2),(3,'Dengue','Mobilize BHWs to conduct structural 4S inspections and distribute bed nets.','high','logistical',1,3),(4,'Dengue','Broadcast community SMS alerts advising residents to wear protective clothing.','medium','public_warning',1,4),(5,'Leptospirosis','Coordinate immediate rodent control sweeps in public markets and trash sectors.','high','environmental',1,1),(6,'Leptospirosis','Dispatch prophylactic Doxycycline capsules to exposed individuals at the health center.','high','medical',1,2),(7,'Leptospirosis','Clear clogged neighborhood drainage channels to lower flood levels.','medium','environmental',1,3),(8,'Leptospirosis','Issue explicit public warnings to avoid wading or swimming in floodwaters.','high','public_warning',1,4),(9,'Acute Gastroenteritis','Issue an immediate Boil Water Advisory for the affected Barangay coordinates.','high','public_warning',1,1),(10,'Acute Gastroenteritis','Dispatch sanitarians to collect deep well and water pump samples for coliform testing.','high','logistical',1,2),(11,'Acute Gastroenteritis','Deploy bulk quantities of Oral Rehydration Salts (ORS) and Zinc to local clinics.','high','medical',1,3),(12,'Acute Gastroenteritis','Enforce strict food safety and hand hygiene campaigns at local neighborhood stalls.','medium','public_warning',1,4),(13,'Respiratory Illness','Implement temporary mandatory masking zones in public indoor spaces and schools.','high','public_warning',1,1),(14,'Respiratory Illness','Advise symptomatic individuals to undergo a 5-to-7 day home isolation protocol.','medium','medical',1,2),(15,'Respiratory Illness','Pre-position influenza therapeutics and respiratory testing swabs at the local clinic.','medium','logistical',1,3),(16,'Hand, Foot, and Mouth Disease','Enforce rigorous chlorine-based decontamination of surfaces, toys, and doorknobs.','high','environmental',1,1),(17,'Hand, Foot, and Mouth Disease','Implement temporary classroom suspensions for daycare centers showing active clusters.','high','logistical',1,2),(18,'Hand, Foot, and Mouth Disease','Train daycare staff to conduct visual checks on children\'s hands, feet, and mouths.','medium','medical',1,3);
/*!40000 ALTER TABLE `mitigation_protocols` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `ml_ai_predictions`
--

DROP TABLE IF EXISTS `ml_ai_predictions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ml_ai_predictions` (
  `prediction_id` int NOT NULL AUTO_INCREMENT,
  `disease_type` varchar(100) NOT NULL,
  `risk_score` double NOT NULL,
  `prediction_probability` double NOT NULL,
  `severity_level` varchar(50) NOT NULL,
  `algorithm_used` varchar(100) NOT NULL,
  `prediction_date` datetime(6) NOT NULL,
  PRIMARY KEY (`prediction_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `ml_ai_predictions`
--

LOCK TABLES `ml_ai_predictions` WRITE;
/*!40000 ALTER TABLE `ml_ai_predictions` DISABLE KEYS */;
/*!40000 ALTER TABLE `ml_ai_predictions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `notification`
--

DROP TABLE IF EXISTS `notification`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `notification` (
  `notification_id` int NOT NULL AUTO_INCREMENT,
  `recipient_role` varchar(100) NOT NULL,
  `notification_message` longtext NOT NULL,
  `sent_date` datetime(6) NOT NULL,
  `alert_id` int NOT NULL,
  PRIMARY KEY (`notification_id`),
  KEY `notification_alert_id_499f3ee2_fk_alerts_alert_id` (`alert_id`),
  CONSTRAINT `notification_alert_id_499f3ee2_fk_alerts_alert_id` FOREIGN KEY (`alert_id`) REFERENCES `alerts` (`alert_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `notification`
--

LOCK TABLES `notification` WRITE;
/*!40000 ALTER TABLE `notification` DISABLE KEYS */;
/*!40000 ALTER TABLE `notification` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `notification_logs`
--

DROP TABLE IF EXISTS `notification_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `notification_logs` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `alert_id` bigint NOT NULL,
  `recipient_role` varchar(30) NOT NULL,
  `recipient_name` varchar(200) DEFAULT NULL,
  `channel` varchar(10) NOT NULL,
  `message_summary` longtext,
  `delivery_status` varchar(10) NOT NULL,
  `sent_at` datetime(6) NOT NULL,
  `read_at` datetime(6) DEFAULT NULL,
  `created_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `notification_logs`
--

LOCK TABLES `notification_logs` WRITE;
/*!40000 ALTER TABLE `notification_logs` DISABLE KEYS */;
/*!40000 ALTER TABLE `notification_logs` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `ocr_results`
--

DROP TABLE IF EXISTS `ocr_results`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ocr_results` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `registration_id` bigint NOT NULL,
  `extracted_text` longtext,
  `extracted_name` varchar(255) DEFAULT NULL,
  `match_score` decimal(5,2) DEFAULT NULL,
  `ocr_status` varchar(12) NOT NULL,
  `processed_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `registration_id` (`registration_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `ocr_results`
--

LOCK TABLES `ocr_results` WRITE;
/*!40000 ALTER TABLE `ocr_results` DISABLE KEYS */;
/*!40000 ALTER TABLE `ocr_results` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `outbreak_threshold_logs`
--

DROP TABLE IF EXISTS `outbreak_threshold_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `outbreak_threshold_logs` (
  `id` int NOT NULL AUTO_INCREMENT,
  `disease_label` varchar(150) NOT NULL,
  `pidsr_category` varchar(32) NOT NULL,
  `confirmed_count` smallint unsigned NOT NULL,
  `threshold_status` varchar(32) NOT NULL,
  `warning_threshold` smallint unsigned DEFAULT NULL,
  `outbreak_threshold` smallint unsigned DEFAULT NULL,
  `time_window_days` smallint unsigned NOT NULL,
  `actor_id` int unsigned DEFAULT NULL,
  `created_at` datetime(6) NOT NULL,
  `barangay_id` bigint NOT NULL,
  `report_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  CONSTRAINT `outbreak_threshold_logs_chk_1` CHECK ((`confirmed_count` >= 0)),
  CONSTRAINT `outbreak_threshold_logs_chk_2` CHECK ((`warning_threshold` >= 0)),
  CONSTRAINT `outbreak_threshold_logs_chk_3` CHECK ((`outbreak_threshold` >= 0)),
  CONSTRAINT `outbreak_threshold_logs_chk_4` CHECK ((`time_window_days` >= 0)),
  CONSTRAINT `outbreak_threshold_logs_chk_5` CHECK ((`actor_id` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `outbreak_threshold_logs`
--

LOCK TABLES `outbreak_threshold_logs` WRITE;
/*!40000 ALTER TABLE `outbreak_threshold_logs` DISABLE KEYS */;
INSERT INTO `outbreak_threshold_logs` VALUES (1,'Undetermined','Category 2',1,'ISOLATED_CASE',2,3,7,1,'2026-06-25 14:05:53.805815',20,4);
/*!40000 ALTER TABLE `outbreak_threshold_logs` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `patient_cases`
--

DROP TABLE IF EXISTS `patient_cases`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `patient_cases` (
  `id` int NOT NULL AUTO_INCREMENT,
  `sequence_no` int unsigned NOT NULL,
  `purok_street` longtext NOT NULL,
  `latitude` decimal(10,7) DEFAULT NULL,
  `longitude` decimal(10,7) DEFAULT NULL,
  `date_of_onset` date DEFAULT NULL,
  `symptoms_json` longtext NOT NULL,
  `fever_duration` smallint unsigned DEFAULT NULL,
  `created_at` datetime(6) NOT NULL,
  `barangay_id` bigint NOT NULL,
  `session_id` int NOT NULL,
  `report_id` bigint DEFAULT NULL,
  `age` smallint unsigned NOT NULL,
  `sex` varchar(10) NOT NULL,
  `patient_name` varchar(255) NOT NULL DEFAULT 'Unknown Resident',
  `civil_status` varchar(50) DEFAULT NULL,
  `date_of_birth` date DEFAULT NULL,
  `detailed_address` text,
  `is_student` tinyint(1) NOT NULL DEFAULT '0',
  `grade_year_section` varchar(100) DEFAULT NULL,
  `school_name` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  CONSTRAINT `patient_cases_chk_1` CHECK ((`sequence_no` >= 0)),
  CONSTRAINT `patient_cases_chk_2` CHECK ((`fever_duration` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `patient_cases`
--

LOCK TABLES `patient_cases` WRITE;
/*!40000 ALTER TABLE `patient_cases` DISABLE KEYS */;
INSERT INTO `patient_cases` VALUES (1,1,'Purok 1',NULL,NULL,'2026-01-15','[\"fever_high\", \"body_ache\", \"petechiae_bleeding\"]',NULL,'2026-06-15 07:11:00.639275',1,1,2,8,'Female','Unknown Resident',NULL,NULL,NULL,0,NULL,NULL),(2,1,'purok',10.5402216,122.8338713,'2026-06-15','[\"fever_high\", \"fatigue\", \"limb_weakness\", \"cough_paroxysms\", \"throat_pseudomembrane\", \"abdominal_cramps\", \"jaundice\", \"maculopapular_rash\", \"endemic_travel\"]',NULL,'2026-06-15 07:12:36.427161',20,2,3,11,'Male','Unknown Resident',NULL,NULL,NULL,0,NULL,NULL),(3,1,'purok 5',10.5404271,122.8391247,'2026-06-21','[\"chills\"]',NULL,'2026-06-21 15:20:32.404454',20,3,4,15,'Male','Unknown Resident',NULL,NULL,NULL,0,NULL,NULL),(4,2,'purok 5',10.5404077,122.8391070,'2026-06-21','[\"chills\"]',NULL,'2026-06-21 15:20:32.404454',20,3,5,9,'Female','Unknown Resident',NULL,NULL,NULL,0,NULL,NULL),(5,3,'purok 5',10.5403454,122.8391176,'2026-06-21','[\"chills\"]',NULL,'2026-06-21 15:20:32.404454',20,3,6,25,'Female','Unknown Resident',NULL,NULL,NULL,0,NULL,NULL),(6,4,'purok 5',10.5403317,122.8391404,'2026-06-21','[\"chills\"]',NULL,'2026-06-21 15:20:32.404454',20,3,7,35,'Male','Unknown Resident',NULL,NULL,NULL,0,NULL,NULL),(7,5,'purok 5',10.5403423,122.8391311,'2026-06-21','[\"chills\"]',NULL,'2026-06-21 15:20:32.404454',20,3,8,21,'Female','Unknown Resident',NULL,NULL,NULL,0,NULL,NULL);
/*!40000 ALTER TABLE `patient_cases` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `patient_cases_symptoms`
--

DROP TABLE IF EXISTS `patient_cases_symptoms`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `patient_cases_symptoms` (
  `id` int NOT NULL AUTO_INCREMENT,
  `patientcase_id` int NOT NULL,
  `symptom_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `patient_cases_symptoms_patientcase_id_symptom_id_e2c2a1e1_uniq` (`patientcase_id`,`symptom_id`),
  KEY `patient_cases_symptoms_symptom_id_2ea37154_fk_symptoms_id` (`symptom_id`),
  CONSTRAINT `patient_cases_sympto_patientcase_id_35cc4512_fk_patient_c` FOREIGN KEY (`patientcase_id`) REFERENCES `patient_cases` (`id`),
  CONSTRAINT `patient_cases_symptoms_symptom_id_2ea37154_fk_symptoms_id` FOREIGN KEY (`symptom_id`) REFERENCES `symptoms` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `patient_cases_symptoms`
--

LOCK TABLES `patient_cases_symptoms` WRITE;
/*!40000 ALTER TABLE `patient_cases_symptoms` DISABLE KEYS */;
INSERT INTO `patient_cases_symptoms` VALUES (1,3,4),(2,4,4),(3,5,4),(4,6,4),(5,7,4);
/*!40000 ALTER TABLE `patient_cases_symptoms` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `patients`
--

DROP TABLE IF EXISTS `patients`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `patients` (
  `patient_id` int NOT NULL AUTO_INCREMENT,
  `full_name` varchar(255) NOT NULL,
  `sex` varchar(10) NOT NULL,
  `address` longtext NOT NULL,
  `birthdate` date NOT NULL,
  `barangay_id` int NOT NULL,
  PRIMARY KEY (`patient_id`),
  KEY `patients_barangay_id_2d28180a_fk_barangays_barangay_id` (`barangay_id`),
  CONSTRAINT `patients_barangay_id_2d28180a_fk_barangays_barangay_id` FOREIGN KEY (`barangay_id`) REFERENCES `barangays` (`barangay_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `patients`
--

LOCK TABLES `patients` WRITE;
/*!40000 ALTER TABLE `patients` DISABLE KEYS */;
/*!40000 ALTER TABLE `patients` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `registration_requests`
--

DROP TABLE IF EXISTS `registration_requests`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `registration_requests` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `first_name` varchar(100) NOT NULL,
  `last_name` varchar(100) NOT NULL,
  `middle_name` varchar(100) DEFAULT NULL,
  `suffix` varchar(20) DEFAULT NULL,
  `birthdate` date DEFAULT NULL,
  `id_type` varchar(50) DEFAULT NULL,
  `id_number` varchar(100) DEFAULT NULL,
  `email` varchar(255) NOT NULL,
  `contact_number` varchar(20) DEFAULT NULL,
  `password_hash` varchar(255) NOT NULL,
  `region_text` varchar(100) DEFAULT NULL,
  `province_text` varchar(100) DEFAULT NULL,
  `city_text` varchar(100) DEFAULT NULL,
  `barangay_text` varchar(100) DEFAULT NULL,
  `approval_status` varchar(10) NOT NULL,
  `rejection_reason` longtext,
  `document_path` varchar(500) DEFAULT NULL,
  `submitted_at` datetime(6) NOT NULL,
  `reviewed_at` datetime(6) DEFAULT NULL,
  `reviewed_by` bigint DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `registration_requests`
--

LOCK TABLES `registration_requests` WRITE;
/*!40000 ALTER TABLE `registration_requests` DISABLE KEYS */;
/*!40000 ALTER TABLE `registration_requests` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `risk_analysis`
--

DROP TABLE IF EXISTS `risk_analysis`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `risk_analysis` (
  `analysis_id` int NOT NULL AUTO_INCREMENT,
  `risk_score` double NOT NULL,
  `anomaly_flag` tinyint(1) NOT NULL,
  `analysis_date` datetime(6) NOT NULL,
  `prediction_id` int NOT NULL,
  PRIMARY KEY (`analysis_id`),
  KEY `risk_analysis_prediction_id_9e7f8040_fk_ml_ai_pre` (`prediction_id`),
  CONSTRAINT `risk_analysis_prediction_id_9e7f8040_fk_ml_ai_pre` FOREIGN KEY (`prediction_id`) REFERENCES `ml_ai_predictions` (`prediction_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `risk_analysis`
--

LOCK TABLES `risk_analysis` WRITE;
/*!40000 ALTER TABLE `risk_analysis` DISABLE KEYS */;
/*!40000 ALTER TABLE `risk_analysis` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `risk_assessments`
--

DROP TABLE IF EXISTS `risk_assessments`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `risk_assessments` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `report_id` bigint NOT NULL,
  `barangay_id` bigint NOT NULL,
  `anomaly_score` decimal(8,4) DEFAULT NULL,
  `risk_score` decimal(8,4) DEFAULT NULL,
  `risk_level` varchar(10) NOT NULL,
  `model_version` varchar(50) DEFAULT NULL,
  `evaluation_status` varchar(10) NOT NULL,
  `evaluated_at` datetime(6) DEFAULT NULL,
  `recommended_action` longtext,
  `created_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `risk_assessments`
--

LOCK TABLES `risk_assessments` WRITE;
/*!40000 ALTER TABLE `risk_assessments` DISABLE KEYS */;
INSERT INTO `risk_assessments` VALUES (1,1,20,0.5000,0.2500,'low','rule-v1','completed','2026-06-13 13:24:22.867516','No immediate action required for Dengue.','2026-06-13 13:24:22.867516'),(2,3,20,0.3000,0.2500,'low','rule-v1','completed','2026-06-15 07:15:51.855797','No immediate action required for Undetermined.','2026-06-15 07:15:51.855797'),(3,2,1,0.3000,0.2500,'low','rule-v1','completed','2026-06-19 07:22:58.050890','No immediate action required for Undetermined.','2026-06-19 07:22:58.050890'),(4,4,20,-0.5268,0.5000,'moderate','random-forest-v1','completed','2026-06-21 15:20:32.460182','Continue routine monitoring for Undetermined.','2026-06-21 15:20:32.460182'),(5,5,20,-0.5319,0.5000,'moderate','random-forest-v1','completed','2026-06-21 15:20:32.507498','Continue routine monitoring for Dengue.','2026-06-21 15:20:32.507498'),(6,6,20,-0.5201,0.5000,'moderate','random-forest-v1','completed','2026-06-21 15:20:32.535819','Continue routine monitoring for Undetermined.','2026-06-21 15:20:32.535819'),(7,7,20,-0.5210,0.5000,'moderate','random-forest-v1','completed','2026-06-21 15:20:32.565813','Continue routine monitoring for Undetermined.','2026-06-21 15:20:32.565813'),(8,8,20,-0.5226,0.5000,'moderate','random-forest-v1','completed','2026-06-21 15:20:32.596878','Continue routine monitoring for Undetermined.','2026-06-21 15:20:32.596878');
/*!40000 ALTER TABLE `risk_assessments` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `sessions`
--

DROP TABLE IF EXISTS `sessions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sessions` (
  `id` varchar(128) NOT NULL,
  `user_id` int unsigned NOT NULL,
  `user_type` varchar(15) NOT NULL,
  `ip_address` varchar(45) DEFAULT NULL,
  `user_agent` varchar(500) DEFAULT NULL,
  `created_at` datetime(6) NOT NULL,
  `expires_at` datetime(6) NOT NULL,
  `invalidated` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`),
  CONSTRAINT `sessions_chk_1` CHECK ((`user_id` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `sessions`
--

LOCK TABLES `sessions` WRITE;
/*!40000 ALTER TABLE `sessions` DISABLE KEYS */;
INSERT INTO `sessions` VALUES ('906h5mnyhmje55zdvdn6f9r42391boi6',1,'admin','127.0.0.1','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36','2026-07-02 15:15:27.684652','2026-07-02 17:15:27.684652',1);
/*!40000 ALTER TABLE `sessions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `super_admin`
--

DROP TABLE IF EXISTS `super_admin`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `super_admin` (
  `super_admin_id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `email` varchar(254) NOT NULL,
  `password` varchar(255) NOT NULL,
  `role` varchar(50) NOT NULL,
  `status` varchar(50) NOT NULL,
  PRIMARY KEY (`super_admin_id`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `super_admin`
--

LOCK TABLES `super_admin` WRITE;
/*!40000 ALTER TABLE `super_admin` DISABLE KEYS */;
/*!40000 ALTER TABLE `super_admin` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `super_admins`
--

DROP TABLE IF EXISTS `super_admins`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `super_admins` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `username` varchar(100) NOT NULL,
  `first_name` varchar(100) NOT NULL,
  `last_name` varchar(100) NOT NULL,
  `middle_name` varchar(100) DEFAULT NULL,
  `suffix` varchar(20) DEFAULT NULL,
  `email` varchar(255) NOT NULL,
  `contact_number` varchar(20) DEFAULT NULL,
  `password_hash` varchar(255) NOT NULL,
  `profile_image` varchar(500) DEFAULT NULL,
  `status` varchar(10) NOT NULL,
  `remember_token` varchar(255) DEFAULT NULL,
  `token_expiry` datetime(6) DEFAULT NULL,
  `last_login` datetime(6) DEFAULT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `super_admins`
--

LOCK TABLES `super_admins` WRITE;
/*!40000 ALTER TABLE `super_admins` DISABLE KEYS */;
INSERT INTO `super_admins` VALUES (1,'superadmin','System','Super Administrator',NULL,NULL,'superadmin@pulse.local',NULL,'$2b$12$HnQu8V9who5yMKnGIDr4lOq6s0loSBI4EBXLpvMWGpxEzIoZ2zDd.',NULL,'active',NULL,NULL,'2026-06-22 14:48:35.032615','2026-06-10 15:47:29.945801','2026-06-10 15:47:29.945801');
/*!40000 ALTER TABLE `super_admins` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `surveillance_reports`
--

DROP TABLE IF EXISTS `surveillance_reports`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `surveillance_reports` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `barangay_id` bigint NOT NULL,
  `submitted_by` bigint DEFAULT NULL,
  `source_type` varchar(20) NOT NULL,
  `syndrome_type` varchar(150) NOT NULL,
  `suspected_disease` varchar(150) DEFAULT NULL,
  `case_count` int unsigned NOT NULL,
  `date_of_onset` date DEFAULT NULL,
  `report_date` datetime(6) NOT NULL,
  `case_classification` varchar(10) NOT NULL,
  `latitude` decimal(10,7) DEFAULT NULL,
  `longitude` decimal(10,7) DEFAULT NULL,
  `validation_status` varchar(10) NOT NULL,
  `validated_by` bigint DEFAULT NULL,
  `remarks` longtext,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `patient_id` int DEFAULT NULL,
  `status` varchar(20) NOT NULL,
  `confirmed_at` datetime(6) DEFAULT NULL,
  `session_id` int DEFAULT NULL,
  `is_anomaly` tinyint(1) NOT NULL,
  `ml_anomaly_score` decimal(8,4) DEFAULT NULL,
  `epidemic_threshold_status` varchar(32) NOT NULL,
  `patient_name` varchar(255) NOT NULL DEFAULT 'Unknown Resident',
  `civil_status` varchar(50) DEFAULT NULL,
  `date_of_birth` date DEFAULT NULL,
  `detailed_address` text,
  `is_student` tinyint(1) NOT NULL DEFAULT '0',
  `grade_year_section` varchar(100) DEFAULT NULL,
  `school_name` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_surveillance_reports_patient` (`patient_id`),
  KEY `surveillance_reports_session_id_91d3eb5b_fk_surveilla` (`session_id`),
  CONSTRAINT `fk_surveillance_reports_patient` FOREIGN KEY (`patient_id`) REFERENCES `patients` (`patient_id`) ON DELETE SET NULL,
  CONSTRAINT `surveillance_reports_session_id_91d3eb5b_fk_surveilla` FOREIGN KEY (`session_id`) REFERENCES `surveillance_sessions` (`id`),
  CONSTRAINT `surveillance_reports_chk_1` CHECK ((`case_count` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `surveillance_reports`
--

LOCK TABLES `surveillance_reports` WRITE;
/*!40000 ALTER TABLE `surveillance_reports` DISABLE KEYS */;
INSERT INTO `surveillance_reports` VALUES (1,20,1,'BHW','Dengue',NULL,7,'2026-06-13','2026-06-13 13:23:26.884395','probable',10.5355120,122.8349077,'validated',1,NULL,'2026-06-13 13:23:26.884395','2026-06-13 13:24:32.412986',NULL,'Confirmed','2026-06-13 13:24:32.412986',NULL,0,NULL,'','Unknown Resident',NULL,NULL,NULL,0,NULL,NULL),(2,1,1,'BHW','Undetermined',NULL,1,'2026-01-15','2026-06-15 07:11:00.639275','unassigned',NULL,NULL,'validated',1,NULL,'2026-06-15 07:11:00.639275','2026-06-15 07:11:00.639275',NULL,'Unclassified',NULL,1,0,NULL,'','Unknown Resident',NULL,NULL,NULL,0,NULL,NULL),(3,20,1,'BHW','Undetermined',NULL,1,'2026-06-15','2026-06-15 07:12:36.427161','unassigned',10.5402216,122.8338713,'validated',1,NULL,'2026-06-15 07:12:36.427161','2026-06-15 07:12:36.427161',NULL,'Unclassified',NULL,2,0,NULL,'','Unknown Resident',NULL,NULL,NULL,0,NULL,NULL),(4,20,1,'BHW','Undetermined','Undetermined',1,'2026-06-21','2026-06-21 15:20:32.404454','confirmed',10.5404271,122.8391247,'validated',NULL,'Age: 15 | Sex: Male | Address: purok 5 | ML Classification: Undetermined | Symptoms: Chills or Rigors | Lab Control #: ff safhsgfshffh | Test Type: PCR','2026-06-21 15:20:32.404454','2026-06-25 14:05:53.805815',NULL,'Confirmed','2026-06-25 14:05:53.772791',3,0,-0.5268,'ISOLATED_CASE','Unknown Resident',NULL,NULL,NULL,0,NULL,NULL),(5,20,1,'BHW','Dengue','Dengue',1,'2026-06-21','2026-06-21 15:20:32.404454','probable',10.5404077,122.8391070,'validated',NULL,'Age: 9 | Sex: Female | Address: purok 5 | ML Classification: Dengue | Symptoms: Chills or Rigors','2026-06-21 15:20:32.404454','2026-06-21 15:20:32.404454',NULL,'Probable',NULL,3,0,-0.5319,'','Unknown Resident',NULL,NULL,NULL,0,NULL,NULL),(6,20,1,'BHW','Undetermined','Undetermined',1,'2026-06-21','2026-06-21 15:20:32.404454','unassigned',10.5403454,122.8391176,'validated',NULL,'Age: 25 | Sex: Female | Address: purok 5 | ML Classification: Undetermined | Symptoms: Chills or Rigors','2026-06-21 15:20:32.404454','2026-06-21 15:20:32.404454',NULL,'Probable',NULL,3,0,-0.5201,'','Unknown Resident',NULL,NULL,NULL,0,NULL,NULL),(7,20,1,'BHW','Undetermined','Undetermined',1,'2026-06-21','2026-06-21 15:20:32.404454','unassigned',10.5403317,122.8391404,'validated',NULL,'Age: 35 | Sex: Male | Address: purok 5 | ML Classification: Undetermined | Symptoms: Chills or Rigors','2026-06-21 15:20:32.404454','2026-06-21 15:20:32.404454',NULL,'Probable',NULL,3,0,-0.5210,'','Unknown Resident',NULL,NULL,NULL,0,NULL,NULL),(8,20,1,'BHW','Undetermined','Undetermined',1,'2026-06-21','2026-06-21 15:20:32.404454','unassigned',10.5403423,122.8391311,'validated',NULL,'Age: 21 | Sex: Female | Address: purok 5 | ML Classification: Undetermined | Symptoms: Chills or Rigors','2026-06-21 15:20:32.404454','2026-06-21 15:20:32.404454',NULL,'Probable',NULL,3,0,-0.5226,'','Unknown Resident',NULL,NULL,NULL,0,NULL,NULL);
/*!40000 ALTER TABLE `surveillance_reports` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `surveillance_sessions`
--

DROP TABLE IF EXISTS `surveillance_sessions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `surveillance_sessions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `case_classification` varchar(10) NOT NULL,
  `syndrome_type` varchar(150) NOT NULL,
  `source_type` varchar(20) NOT NULL,
  `patient_count` int unsigned NOT NULL,
  `session_date` datetime(6) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `submitted_by` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `surveillance_sessions_submitted_by_e73a5298_fk_users_id` (`submitted_by`),
  CONSTRAINT `surveillance_sessions_submitted_by_e73a5298_fk_users_id` FOREIGN KEY (`submitted_by`) REFERENCES `users` (`id`),
  CONSTRAINT `surveillance_sessions_chk_1` CHECK ((`patient_count` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `surveillance_sessions`
--

LOCK TABLES `surveillance_sessions` WRITE;
/*!40000 ALTER TABLE `surveillance_sessions` DISABLE KEYS */;
INSERT INTO `surveillance_sessions` VALUES (1,'unassigned','Undetermined','BHW',1,'2026-06-15 07:11:00.639275','2026-06-15 07:11:00.639275','2026-06-15 07:11:00.639275',1),(2,'unassigned','Undetermined','BHW',1,'2026-06-15 07:12:36.427161','2026-06-15 07:12:36.427161','2026-06-15 07:12:36.427161',1),(3,'unassigned','Undetermined','BHW',5,'2026-06-21 15:20:32.404454','2026-06-21 15:20:32.404454','2026-06-21 15:20:32.404454',1);
/*!40000 ALTER TABLE `surveillance_sessions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `symptoms`
--

DROP TABLE IF EXISTS `symptoms`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `symptoms` (
  `id` int NOT NULL AUTO_INCREMENT,
  `code` varchar(64) NOT NULL,
  `name` varchar(255) NOT NULL,
  `syndromic_group` varchar(1) NOT NULL,
  `description` longtext NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `code` (`code`)
) ENGINE=InnoDB AUTO_INCREMENT=40 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `symptoms`
--

LOCK TABLES `symptoms` WRITE;
/*!40000 ALTER TABLE `symptoms` DISABLE KEYS */;
INSERT INTO `symptoms` VALUES (1,'fever_high','High Fever (≥38°C)','A',''),(2,'fever_low','Low-grade Fever','A',''),(3,'fever_step_ladder','Prolonged Step-Ladder Fever','A',''),(4,'chills','Chills or Rigors','A',''),(5,'headache','Severe Headache','A',''),(6,'body_ache','Generalized Muscle/Joint/Bone Pain','A',''),(7,'calf_tenderness','Intense Calf Muscle Tenderness','A',''),(8,'fatigue','Extreme Fatigue / Exhaustion','A',''),(9,'limb_weakness','Sudden Limb Weakness or Floppy Muscles','A',''),(10,'body_spasms','Generalized Body Spasms or Muscle Rigidity','A',''),(11,'cough_dry','Persistent Dry Cough','B',''),(12,'cough_paroxysms','Severe Productive / Fits of Coughing','B',''),(13,'inspiratory_whoop','Loud High-Pitched Sound on Breathing In','B',''),(14,'sore_throat','Acute Sore Throat','B',''),(15,'runny_nose','Runny Nose / Coryza','B',''),(16,'conjunctivitis','Bloodshot, Watery Red Eyes','B',''),(17,'conjunctival_suffusion','Red Eyes WITHOUT Pus/Discharge','B',''),(18,'dyspnea','Shortness of Breath / Difficulty Breathing','B',''),(19,'throat_pseudomembrane','Adherent Grayish-White Membrane in Throat','B',''),(20,'bull_neck','Massive Swelling of the Neck (\"Bull Neck\")','B',''),(21,'diarrhea_watery','Profuse Watery Diarrhea / Rice-Water Stools','C',''),(22,'diarrhea_bloody','Visible Blood in Loose Stools','C',''),(23,'vomiting','Persistent Nausea or Vomiting','C',''),(24,'post_tussive_vomiting','Vomiting Immediately After Coughing','C',''),(25,'abdominal_cramps','Severe Abdominal Cramps or Bloating','C',''),(26,'jaundice','Jaundice / Yellow Skin or Eyes','C',''),(27,'dark_urine','Dark, Tea-Colored Urine','C',''),(28,'mouth_sores','Painful Mouth Ulcers / Tongue Sores','D',''),(29,'hand_foot_blisters','Small Blisters on Palms of Hands / Soles of Feet','D',''),(30,'maculopapular_rash','Generalized Red, Flat Rash Spreading Downwards','D',''),(31,'petechiae_bleeding','Tiny Purple Skin Dots / Spontaneous Nosebleeds','D',''),(32,'black_eschar','Distinct Skin Ulcer with a Black Center','D',''),(33,'hydrophobia','Hydrophobia (Muscle Spasms When Swallowing Water)','D',''),(34,'animal_bite','History of Animal Bite/Scratch','E',''),(35,'floodwater_exposure','History of Wading in Floodwaters or Mud','E',''),(36,'endemic_travel','Recent Travel to Jungle/Mountainous Area','E',''),(37,'poultry_exposure','Exposure to Sick or Dead Poultry/Birds','E',''),(38,'post_vaccine','Symptoms Started Within 30 Days of Receiving a Vaccine','E',''),(39,'neonatal_suck_failure','Normal Crying/Sucking for First 2 Days of Life, then Stopped','E','');
/*!40000 ALTER TABLE `symptoms` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `system_logs`
--

DROP TABLE IF EXISTS `system_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `system_logs` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_role` varchar(50) DEFAULT NULL,
  `user_id` int unsigned DEFAULT NULL,
  `activity_type` varchar(100) NOT NULL,
  `module` varchar(100) DEFAULT NULL,
  `ip_address` varchar(45) DEFAULT NULL,
  `log_message` longtext NOT NULL,
  `log_level` varchar(10) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `user_display_name` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  CONSTRAINT `system_logs_chk_1` CHECK ((`user_id` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=66 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `system_logs`
--

LOCK TABLES `system_logs` WRITE;
/*!40000 ALTER TABLE `system_logs` DISABLE KEYS */;
INSERT INTO `system_logs` VALUES (1,'admin',1,'login_success','accounts','127.0.0.1','admin login: admin@pulse.local','info','2026-06-10 15:51:25.570978',NULL),(2,'admin',1,'login_success','accounts','127.0.0.1','admin login: admin@pulse.local','info','2026-06-13 13:21:03.328624',NULL),(3,'barangay_health_worker',1,'login_success','accounts','127.0.0.1','user login: betitak35@gmail.com','info','2026-06-13 13:21:58.386089',NULL),(4,'barangay_health_worker',1,'report_submitted','reports','127.0.0.1','Report #1 submitted for barangay #20.','info','2026-06-13 13:23:26.893389',NULL),(5,'admin',1,'login_success','accounts','127.0.0.1','admin login: admin@pulse.local','info','2026-06-13 13:23:38.032890',NULL),(6,'barangay_health_worker',1,'login_success','accounts','127.0.0.1','user login: betitak35@gmail.com','info','2026-06-13 13:51:41.785912',NULL),(7,'admin',1,'login_success','accounts','127.0.0.1','admin login: admin@pulse.local','info','2026-06-14 14:39:32.482359',NULL),(8,'admin',1,'login_success','accounts','127.0.0.1','admin login: admin@pulse.local','info','2026-06-14 14:50:28.854623',NULL),(9,'admin',1,'login_success','accounts','127.0.0.1','admin login: admin@pulse.local','info','2026-06-15 06:27:46.436493',NULL),(10,'barangay_health_worker',1,'login_success','accounts','127.0.0.1','user login: betitak35@gmail.com','info','2026-06-15 06:28:03.656022',NULL),(11,'barangay_health_worker',1,'batch_report_submitted','reports','127.0.0.1','Session #2 with 1 patient case(s) submitted.','info','2026-06-15 07:12:36.444349',NULL),(12,'admin',1,'login_success','accounts','127.0.0.1','admin login: admin@pulse.local','info','2026-06-15 07:12:52.685165',NULL),(13,'barangay_health_worker',1,'login_success','accounts','127.0.0.1','user login: betitak35@gmail.com','info','2026-06-15 07:29:04.543621',NULL),(14,'admin',1,'login_success','accounts','127.0.0.1','admin login: admin@pulse.local','info','2026-06-16 19:05:13.889199',NULL),(15,'admin',1,'login_success','accounts','127.0.0.1','admin login: admin@pulse.local','info','2026-06-16 19:55:27.368093',NULL),(16,'barangay_health_worker',2,'login_success','accounts','127.0.0.1','user login: test@gmail.com','info','2026-06-16 19:57:04.751904',NULL),(17,'admin',1,'login_success','accounts','127.0.0.1','admin login: admin@pulse.local','info','2026-06-19 06:43:33.692802',NULL),(18,'barangay_health_worker',1,'login_success','accounts','127.0.0.1','user login: betitak35@gmail.com','info','2026-06-19 07:10:58.865646',NULL),(19,'admin',1,'login_success','accounts','127.0.0.1','admin login: admin@pulse.local','info','2026-06-19 07:21:38.425755',NULL),(20,'admin',1,'login_success','accounts','127.0.0.1','admin login: admin@pulse.local','info','2026-06-19 07:22:13.149185',NULL),(21,'admin',1,'login_success','accounts','127.0.0.1','admin login: admin@pulse.local','info','2026-06-21 13:42:25.718451',NULL),(22,'barangay_health_worker',1,'login_success','accounts','127.0.0.1','user login: betitak35@gmail.com','info','2026-06-21 15:17:46.091477',NULL),(23,'barangay_health_worker',1,'batch_report_submitted','reports','127.0.0.1','Session #3 with 5 patient case(s) submitted.','info','2026-06-21 15:20:32.602876',NULL),(24,'admin',1,'login_success','accounts','127.0.0.1','admin login: admin@pulse.local','info','2026-06-21 15:22:56.017170',NULL),(25,'barangay_health_worker',1,'login_success','accounts','127.0.0.1','user login: betitak35@gmail.com','info','2026-06-21 15:43:03.541998','Jaykirt M Betita'),(26,'admin',1,'login_success','accounts','127.0.0.1','admin login: admin@pulse.local','info','2026-06-21 15:43:13.746242','System Administrator'),(27,'barangay_health_worker',1,'login_success','accounts','127.0.0.1','user login: betitak35@gmail.com','info','2026-06-21 15:43:34.571166','Jaykirt M Betita'),(28,'admin',1,'login_success','accounts','127.0.0.1','admin login: admin@pulse.local','info','2026-06-21 15:45:25.831787','System Administrator'),(29,'barangay_health_worker',1,'login_success','accounts','127.0.0.1','user login: betitak35@gmail.com','info','2026-06-21 15:51:03.808080','Jaykirt M Betita'),(30,'admin',1,'login_success','accounts','127.0.0.1','admin login: admin@pulse.local','info','2026-06-21 15:53:52.166766','System Administrator'),(31,'admin',1,'login_success','accounts','127.0.0.1','admin login: admin@pulse.local','info','2026-06-22 13:43:20.639825','System Administrator'),(32,'barangay_health_worker',1,'login_success','accounts','127.0.0.1','user login: betitak35@gmail.com','info','2026-06-22 13:46:00.912643','Jaykirt M Betita'),(33,'barangay_health_worker',1,'login_success','accounts','127.0.0.1','user login: betitak35@gmail.com','info','2026-06-22 14:35:02.760418','Jaykirt M Betita'),(34,'super_admin',1,'login_success','accounts','127.0.0.1','super_admin login: superadmin@pulse.local','info','2026-06-22 14:48:35.035793','System Super Administrator'),(35,'barangay_health_worker',1,'login_success','accounts','127.0.0.1','user login: betitak35@gmail.com','info','2026-06-22 14:55:42.574429','Jaykirt M Betita'),(36,'admin',1,'login_success','accounts','127.0.0.1','admin login: admin@pulse.local','info','2026-06-23 06:50:24.568138','System Administrator'),(37,'barangay_health_worker',1,'login_success','accounts','127.0.0.1','user login: betitak35@gmail.com','info','2026-06-23 07:01:24.940621','Jaykirt M Betita'),(38,'admin',1,'login_success','accounts','127.0.0.1','admin login: admin@pulse.local','info','2026-06-23 07:02:50.216103','System Administrator'),(39,'barangay_health_worker',1,'login_success','accounts','127.0.0.1','user login: betitak35@gmail.com','info','2026-06-23 13:41:06.740602','Jaykirt M Betita'),(40,'admin',1,'login_success','accounts','127.0.0.1','admin login: admin@pulse.local','info','2026-06-24 07:13:45.239492','System Administrator'),(41,'barangay_health_worker',1,'login_success','accounts','127.0.0.1','user login: betitak35@gmail.com','info','2026-06-24 14:11:52.476032','Jaykirt M Betita'),(42,'admin',1,'login_success','accounts','127.0.0.1','admin login: admin@pulse.local','info','2026-06-24 15:01:17.782330','System Administrator'),(43,'admin',1,'login_success','accounts','127.0.0.1','admin login: admin@pulse.local','info','2026-06-24 15:03:40.046283','System Administrator'),(44,'admin',1,'login_success','accounts','127.0.0.1','admin login: admin@pulse.local','info','2026-06-24 15:04:36.374857','System Administrator'),(45,'health_officer',4,'login_success','accounts','127.0.0.1','user login: jojowowers@gmail.com','info','2026-06-24 15:06:13.961167','Hernani J Bañez III'),(46,'admin',1,'login_success','accounts','127.0.0.1','admin login: admin@pulse.local','info','2026-06-24 15:15:44.534380','System Administrator'),(47,'admin',1,'login_success','accounts','127.0.0.1','admin login: admin@pulse.local','info','2026-06-24 15:16:49.064822','System Administrator'),(48,'surveillance_officer',5,'login_success','accounts','127.0.0.1','user login: jelynaujero2@gmail.com','info','2026-06-24 15:17:40.561247','Jelyn S Aujero'),(49,'admin',1,'login_success','accounts','127.0.0.1','admin login: admin@pulse.local','info','2026-06-25 13:53:46.999263','System Administrator'),(50,'barangay_health_worker',2,'login_success','accounts','127.0.0.1','user login: test@gmail.com','info','2026-06-25 14:14:29.003291','Test test Test Jr.'),(51,'barangay_health_worker',1,'login_success','accounts','127.0.0.1','user login: betitak35@gmail.com','info','2026-06-27 05:41:43.366846','Jaykirt M Betita'),(52,'admin',1,'login_success','accounts','127.0.0.1','admin login: admin@pulse.local','info','2026-06-29 16:05:54.173471','System Administrator'),(53,'admin',1,'login_success','accounts','127.0.0.1','admin login: admin@pulse.local','info','2026-06-29 16:10:36.028851','System Administrator'),(54,'admin',1,'login_success','accounts','127.0.0.1','admin login: admin@pulse.local','info','2026-06-29 16:40:27.354052','System Administrator'),(55,'admin',1,'login_success','accounts','127.0.0.1','admin login: admin@pulse.local','info','2026-06-30 15:22:53.717136','System Administrator'),(56,'admin',1,'login_success','accounts','127.0.0.1','admin login: admin@pulse.local','info','2026-07-01 12:45:50.988703','System Administrator'),(57,'admin',1,'login_success','accounts','127.0.0.1','admin login: admin@pulse.local','info','2026-07-02 14:54:03.202266','System Administrator'),(58,'barangay_health_worker',6,'login_success','accounts','127.0.0.1','user login: test123@gmail.com','info','2026-07-02 14:55:43.380630','Test t Test'),(59,'barangay_health_worker',6,'login_success','accounts','127.0.0.1','user login: test123@gmail.com','info','2026-07-02 15:10:36.767139','Test t Test'),(60,'admin',1,'login_success','accounts','127.0.0.1','admin login: admin@pulse.local','info','2026-07-02 15:15:26.084749','System Administrator'),(61,'admin',1,'login_success','accounts','127.0.0.1','admin login: admin@pulse.local','info','2026-07-02 15:15:27.694931','System Administrator'),(62,'surveillance_officer',7,'login_success','accounts','127.0.0.1','user login: testjr123@gmail.com','info','2026-07-02 15:19:07.151374','test test test Jr.'),(63,'surveillance_officer',7,'login_success','accounts','127.0.0.1','user login: testjr123@gmail.com','info','2026-07-02 15:20:22.980517','test test test Jr.'),(64,'admin',1,'login_success','accounts','127.0.0.1','admin login: admin@pulse.local','info','2026-07-02 15:22:43.778740','System Administrator'),(65,'admin',1,'login_success','accounts','127.0.0.1','admin login: admin@pulse.local','info','2026-07-02 15:26:07.920498','System Administrator');
/*!40000 ALTER TABLE `system_logs` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `username` varchar(100) NOT NULL,
  `first_name` varchar(100) NOT NULL,
  `last_name` varchar(100) NOT NULL,
  `middle_name` varchar(100) DEFAULT NULL,
  `suffix` varchar(20) DEFAULT NULL,
  `email` varchar(255) NOT NULL,
  `contact_number` varchar(20) DEFAULT NULL,
  `password_hash` varchar(255) NOT NULL,
  `role` varchar(30) NOT NULL,
  `assigned_region` varchar(150) DEFAULT NULL,
  `designation` varchar(150) DEFAULT NULL,
  `assigned_cluster` varchar(150) DEFAULT NULL,
  `license_or_id_no` varchar(100) DEFAULT NULL,
  `birthdate` date DEFAULT NULL,
  `region_text` varchar(100) DEFAULT NULL,
  `province_text` varchar(100) DEFAULT NULL,
  `city_text` varchar(100) DEFAULT NULL,
  `barangay_text` varchar(100) DEFAULT NULL,
  `profile_image` varchar(500) DEFAULT NULL,
  `status` varchar(10) NOT NULL,
  `first_login` tinyint(1) NOT NULL,
  `remember_token` varchar(255) DEFAULT NULL,
  `token_expiry` datetime(6) DEFAULT NULL,
  `last_login` datetime(6) DEFAULT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
INSERT INTO `users` VALUES (1,'jaykirt.betita.1b3da73d','Jaykirt','Betita','M',NULL,'betitak35@gmail.com','09213533852','$2b$12$.dSfESWwfqrIGCvwBIKNr.ULM/0wYWIESqhcPnYEYg22Qr30jL.XW','barangay_health_worker',NULL,NULL,NULL,NULL,'2004-01-11',NULL,NULL,NULL,'Poblacion',NULL,'active',0,NULL,NULL,'2026-06-27 05:41:43.361845','2026-06-13 13:21:48.670686','2026-06-13 13:21:48.670686'),(2,'test.test.baf3fd67','Test','Test','test','Jr.','test@gmail.com','1231231','$2b$12$BHtK7Xi7vSAF2mlOsq1ipeNuLOsks0PxygJf6hp37zGWPn6P01PYS','barangay_health_worker',NULL,NULL,NULL,NULL,'2005-03-12',NULL,NULL,NULL,'Abuanan',NULL,'active',0,NULL,NULL,'2026-06-25 14:14:28.999274','2026-06-16 19:56:19.175472','2026-06-16 19:56:19.175472'),(3,'earl adrian.sarcia.ae42bc03','Earl Adrian','Sarcia','M',NULL,'Earl@gmail.com','09517568097','$2b$12$3rXNFiCXrvaJe85zk0YEzem/Uky2FVgsiwMxnwlwsPEmPhaxSGfFi','surveillance_officer',NULL,NULL,NULL,NULL,'2000-06-17',NULL,NULL,NULL,NULL,NULL,'active',1,NULL,NULL,NULL,'2026-06-24 15:02:59.015707','2026-06-24 15:02:59.015707'),(4,'hernani.bañez.58009f97','Hernani','Bañez','J','III','jojowowers@gmail.com','09213533856','$2b$12$t64lLyXt7c2Ga522lDS5nOcc72V/rD0XeuWzBqBG4cxjneqhB819S','health_officer',NULL,NULL,NULL,NULL,'2004-05-21',NULL,NULL,NULL,NULL,NULL,'active',0,NULL,NULL,'2026-06-24 15:06:13.955171','2026-06-24 15:05:58.485074','2026-06-24 15:05:58.485074'),(5,'jelyn.aujero.b681e6ec','Jelyn','Aujero','S',NULL,'jelynaujero2@gmail.com','09213533858','$2b$12$JRx2V20e9e0T8mFEr0hHreMaD63N1Fp6Q7a8GTF6gP8LSBU7Qks3.','surveillance_officer',NULL,NULL,NULL,NULL,'2005-07-18',NULL,NULL,NULL,NULL,NULL,'active',0,NULL,NULL,'2026-06-24 15:17:40.556730','2026-06-24 15:17:29.791387','2026-06-24 15:17:29.791387'),(6,'test.test.6fcd0878','Test','Test','t',NULL,'test123@gmail.com','09123456789','$2b$12$EEsoE26wKxcjbgFhpv.rX.13gzI5S3fBxaVwRiShT3VTkC/kZVZQi','barangay_health_worker',NULL,NULL,NULL,NULL,'2005-11-07',NULL,NULL,NULL,'Poblacion',NULL,'active',0,NULL,NULL,'2026-07-02 15:10:36.764135','2026-07-02 14:55:21.556221','2026-07-02 14:55:21.556221'),(7,'test.test.65eba6d6','test','test','test','Jr.','testjr123@gmail.com','09213533852','$2b$12$aEgNbUGNLBw.ccf9UqthjOCs7y2lPmMomt1BNgCHKHZDa6BXDzHTK','surveillance_officer',NULL,NULL,NULL,NULL,'1943-09-03',NULL,NULL,NULL,NULL,NULL,'active',0,NULL,NULL,'2026-07-02 15:20:22.978555','2026-07-02 15:18:08.746040','2026-07-02 15:18:08.746040');
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-07-02 23:42:15
