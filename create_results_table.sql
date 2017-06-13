CREATE TABLE IF NOT EXISTS results (
	id INT(11) NOT NULL AUTO_INCREMENT,
	sprint_number INT(11),
	sprint_day INT(2),
	project VARCHAR(100),
	run_name VARCHAR(100),
	passed INT(6),
	failed INT(6),
	blocked INT(6),
	untested INT(6),
	PRIMARY KEY ( id )
);

CREATE TABLE IF NOT EXISTS defects (
	id INT(11) NOT NULL AUTO_INCREMENT,
	sprint_number INT(11),
	sprint_day INT(2),
	jira_project VARCHAR(100),
	newDefects INT(6),
	inDev INT(6),
	reopened INT(6),
	inReview INT(6),
	inQA INT(6),
	verified INT(6),
	closed INT(6),
	PRIMARY KEY ( id )
);

CREATE TABLE IF NOT EXISTS projectMapping (
	jira_project VARCHAR(100),
	project VARCHAR(100),
	PRIMARY KEY ( jira_project )
);

INSERT INTO projectMapping VALUES ("AR", "ADTV and AMP Ranker");
INSERT INTO projectMapping VALUES ("RNB", "Datorama");
INSERT INTO projectMapping VALUES ("PLAT", "Platform");
INSERT INTO projectMapping VALUES ("CCCM", "Campaign Management");
INSERT INTO projectMapping VALUES ("CCR", "Cadreon Console Report");
INSERT INTO projectMapping VALUES ("AMU", "AMP UI");
INSERT INTO projectMapping VALUES ("CCS", "Cadreon Console Shell");
INSERT INTO projectMapping VALUES ("CSF", "Unity Salesforce Integration ");
INSERT INTO projectMapping VALUES ("UTAG", "uTag");
INSERT INTO projectMapping VALUES ("CADMKT", "Marketplace");
INSERT INTO projectMapping VALUES ("ADE", "AMP Data Engine");

CREATE TABLE IF NOT EXISTS storyPoints (
	id INT(11) NOT NULL AUTO_INCREMENT,
	sprint_number INT(11),
	sprint_day INT(2),
	jira_project VARCHAR(100),
	newStories INT(6),
	ready INT(6),
	inDev INT(6),
	reopened INT(6),
	inReview INT(6),
	inQA INT(6),
	verified INT(6),
	closed INT(6),
	PRIMARY KEY ( id )
);

CREATE TABLE IF NOT EXISTS storyTickets (
	id INT(11) NOT NULL AUTO_INCREMENT,
	sprint_number INT(11),
	sprint_day INT(2),
	jira_project VARCHAR(100),
	newStories INT(6),
	ready INT(6),
	inDev INT(6),
	reopened INT(6),
	inReview INT(6),
	inQA INT(6),
	verified INT(6),
	closed INT(6),
	PRIMARY KEY ( id )
);

CREATE TABLE IF NOT EXISTS componentMapping (
	id INT(11) NOT NULL AUTO_INCREMENT,
	project VARCHAR(100),
	component VARCHAR(100),
	versionMethod VARCHAR(100),
	jenkinsProject VARCHAR(100),
	PRIMARY KEY ( id )
);

	
INSERT INTO componentMapping (project, component, versionMethod, jenkinsProject) VALUES ('AMU', 'UI-AMP','/amp/manifest.json','ui-amp');
INSERT INTO componentMapping (project, component, versionMethod, jenkinsProject) VALUES ("AMU", "API-AMP","/apiamp/v1.0/api/info","api-amp");

INSERT INTO componentMapping (project, component, versionMethod, jenkinsProject) VALUES ("CADMKT", "UI-MARKETPLACE","/marketplace/manifest.json","ui-marketplace");
INSERT INTO componentMapping (project, component, versionMethod, jenkinsProject) VALUES ("CADMKT", "API-MARKETPLACE","/marketplace/v1.0/info","api-marketplace");

INSERT INTO componentMapping (project, component, versionMethod, jenkinsProject) VALUES ("AR", "UI-ATV","/atv/manifest.json","ui-advanced-tv");
INSERT INTO componentMapping (project, component, versionMethod, jenkinsProject) VALUES ("AR", "API-ATV","/atv/v1.0/api/info","api-atv");
INSERT INTO componentMapping (project, component, versionMethod, jenkinsProject) VALUES ("AR", "API-JRANKER",NULL,"api-jranker");

INSERT INTO componentMapping (project, component, versionMethod, jenkinsProject) VALUES ("UTAG", "UI-UTAG","/utag/manifest.json","ui-totaltag");
INSERT INTO componentMapping (project, component, versionMethod, jenkinsProject) VALUES ("UTAG", "API-UTAG","/totaltag/v1/info","api-utag");
INSERT INTO componentMapping (project, component, versionMethod, jenkinsProject) VALUES ("UTAG", "BACKEND-UTAG",NULL,"ttag");
INSERT INTO componentMapping (project, component, versionMethod, jenkinsProject) VALUES ("UTAG", "UTAG-PARSER",NULL,"utag-parser");


INSERT INTO componentMapping (project, component, versionMethod, jenkinsProject) VALUES ("CCR", "UI-REPORTING","/reporting/manifest.json","ui-reporting");
INSERT INTO componentMapping (project, component, versionMethod, jenkinsProject) VALUES ("CCR", "API-REPORTING","/reports/v1.0/api/info","api-console-reporting");

INSERT INTO componentMapping (project, component, versionMethod, jenkinsProject) VALUES ("CCS", "UI-SHELL","/shell/manifest.json","/shell/manifest.json","ui-console-shell");
INSERT INTO componentMapping (project, component, versionMethod, jenkinsProject) VALUES ("CCS", "API-SHELL","/shell/v1.0/api/info","/shell/v1.0/api/info","api-console-shell");
INSERT INTO componentMapping (project, component, versionMethod, jenkinsProject) VALUES ("CCS", "NOTIFICATION","/notificenter/v1.0/api/info","/shell/v1.0/api/info","api-console-notificenter");
INSERT INTO componentMapping (project, component, versionMethod, jenkinsProject) VALUES ("CCS", "MOBILE",NULL,"ui-mobile");


INSERT INTO componentMapping (project, component, versionMethod, jenkinsProject) VALUES ("PLAT", "CORE-USER-MGMNT",NULL,"CORE-AUTH-USER-MGMT");
INSERT INTO componentMapping (project, component, versionMethod, jenkinsProject) VALUES ("PLAT", "LAMBDA-USER-MGMNT",NULL,"UM-LAMBDA");
INSERT INTO componentMapping (project, component, versionMethod, jenkinsProject) VALUES ("PLAT", "LAMBDA-AUTHORIZER",NULL,"AUTHORIZER-LAMBDA");

INSERT INTO componentMapping (project, component, versionMethod, jenkinsProject) VALUES ("CCCM", "CM-UI","/cm/manifest.json","ui-campaign-manager");
INSERT INTO componentMapping (project, component, versionMethod, jenkinsProject) VALUES ("CCCM", "CM-API", "/cm/v1.0/api/info","api-console-campaign-manager");


INSERT INTO componentMapping (project, component, versionMethod, jenkinsProject) VALUES ("CCCM", "SCRAPER-API",NULL,"api-scrapevisor");
INSERT INTO componentMapping (project, component, versionMethod, jenkinsProject) VALUES ("CCCM", "UNITY-SCRAPER",NULL,"unity-scrapers");

INSERT INTO componentMapping (project, component, versionMethod, jenkinsProject) VALUES ("CSF", "CSF-API","/csf/v1.0/api/info","api-csf");
INSERT INTO componentMapping (project, component, versionMethod, jenkinsProject) VALUES ("CSF", "CSF-UI","/csf/manifest.json","ui-csf");
INSERT INTO componentMapping (project, component, versionMethod, jenkinsProject) VALUES ("CSF", "CSF-ETL",NULL,"etl-csf");



 	 