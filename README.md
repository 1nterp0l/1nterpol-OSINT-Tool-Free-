
# 🌐 1NTERPOL MATRIX RADAR | Advanced Cyber-Detector Framework

<p align="center">
  <img src="https://img.shields.io/badge/Version-6.0-blue" alt="Version">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/Language-Python-orange" alt="Language">
</p>

## 📖 Introduction
**1NTERPOL Matrix Radar** est une plateforme modulaire d'investigation numérique, conçue pour automatiser les tâches critiques de reconnaissance (Recon) et d'audit de sécurité. Dans un environnement où la collecte d'informations est le pilier de toute enquête, cet outil centralise la puissance de traitement pour offrir une vision claire, structurée et rapide des infrastructures cibles.

Développé en **Python pur**, ce framework élimine la lourdeur des dépendances externes tout en garantissant des performances de classe industrielle grâce à son architecture orientée objet et son moteur de traitement multithread.

---

## 🚀 Fonctionnalités Avancées

### 🔍 Reconnaissance Réseau & Empreinte Digitale
* **Banner Grabbing Aggressif :** Identification précise des services via des handshakes personnalisés. Ne vous contentez plus de savoir qu'un port est ouvert : découvrez la version exacte du logiciel tournant en arrière-plan.
* **Scan de Ports Multithreadé :** Moteur haute performance utilisant `ThreadPoolExecutor` pour scanner des plages entières en un temps record.
* **Analyse de Topologie :** Détection des vecteurs d'attaque et analyse de la réactivité réseau.

### 🛡️ Audit de Sécurité & Veille
* **Hardening Check :** Analyse des en-têtes de sécurité HTTP, vérification de la présence de politiques HSTS, et détection de CMS.
* **DNS Intelligence :** Audit approfondi de la configuration des zones DNS (SPF, DMARC, MX) pour détecter les failles d'usurpation (spoofing) et les mauvaises configurations de domaine.
* **API Enrichment :** Intégration native des flux de données Shodan et VirusTotal pour corréler vos découvertes locales avec des bases de menaces mondiales.

### 📊 Gestion de l'Investigation
* **Base de Données SQLite :** Chaque action est horodatée et archivée localement. Idéal pour le suivi de dossier sur le long terme.
* **Générateur de Rapports :** Exportation automatisée des logs pour structurer vos découvertes.
* **Mode CLI "Ninja" :** Automatisez vos tâches sans interface graphique, parfait pour l'intégration dans des scripts de défense ou de tests d'intrusion.

---

## 🛠️ Architecture du Framework

Le moteur **"The Architect" (v6.0)** est structuré pour permettre une scalabilité maximale :

1. **`CyberTools` (Core) :** Gère la persistance des données et les interfaces de bas niveau.
2. **`Scanner` (Moteur) :** Implémente la logique métier d'analyse réseau et système.
3. **`MenuHandler` (Interface) :** Offre une navigation fluide entre les modules d'investigation.



---

## ⚙️ Installation & Mise en route

### Prérequis
* Python 3.8 ou supérieur.
* Aucune bibliothèque tierce n'est requise (Standard Library uniquement).

### Installation
```bash
# Cloner le dépôt
git clone [https://github.com/votre-nom/interpol-matrix-radar.git](https://github.com/votre-nom/interpol-matrix-radar.git)

# Entrer dans le répertoire
cd interpol-matrix-radar

## 📷 Aperçu

<p align="center">
  <img src="interpol.png" width="900">
</p>

## ⚙️ Installation

```bash
git clone https://github.com/ton-user/interpol-matrix-radar.git

cd interpol-matrix-radar

python main.py
```
