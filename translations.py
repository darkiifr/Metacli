#!/usr/bin/env python3
"""
MetaCLI Translation System

Provides internationalization support for the MetaCLI GUI application.
Includes translations for English, French, Spanish, and German.
"""

import json
from typing import Dict, Any

class TranslationManager:
    """Manages translations for the MetaCLI GUI application."""
    
    def __init__(self, language='English'):
        self.current_language = language
        self.translations = self._load_translations()
    
    def _load_translations(self) -> Dict[str, Dict[str, str]]:
        """Load all translation strings."""
        return {
            'English': {
                # Window titles
                'main_title': 'MetaCLI - Advanced Metadata Extraction Tool v3.0',
                
                # Menu items
                'menu_file': 'File',
                'menu_edit': 'Edit',
                'menu_tools': 'Tools',
                'menu_view': 'View',
                'menu_help': 'Help',
                
                'file_open': 'Open File...',
                'file_open_dir': 'Open Directory...',
                'file_export': 'Export Results...',
                'file_save_report': 'Save Report...',
                'file_recent': 'Recent Files',
                'file_exit': 'Exit',
                
                'edit_copy': 'Copy Results',
                'edit_select_all': 'Select All',
                'edit_find': 'Find...',
                'edit_filter': 'Filter Results...',
                
                'tools_batch': 'Batch Process...',
                'tools_compare': 'Compare Files...',
                'tools_report': 'Generate Report...',
                'tools_settings': 'Settings...',
                'tools_clear_cache': 'Clear Cache',
                
                'view_refresh': 'Refresh',
                'view_hidden': 'Show Hidden Files',
                'view_auto_refresh': 'Auto Refresh',
                'view_expand_all': 'Expand All',
                'view_collapse_all': 'Collapse All',
                
                'help_guide': 'User Guide',
                'help_shortcuts': 'Keyboard Shortcuts',
                'help_cli': 'Command Line Usage',
                'help_updates': 'Check for Updates',
                'help_about': 'About MetaCLI',
                
                # Tab titles
                'tab_scanner': '📁 File Scanner',
                'tab_metadata': '🔍 Metadata Viewer',
                'tab_batch': '⚙️ Batch Operations',
                'tab_settings': '🛠️ Settings',
                
                # Scanner tab
                'scanner_title': 'Directory & File Scanner',
                'scanner_subtitle': 'Scan directories and files to extract metadata',
                'target_selection': 'Target Selection',
                'path_label': 'Path:',
                'browse_directory': '📁 Browse Directory',
                'select_file': '📄 Select File',
                'home_button': '🏠 Home',
                'desktop_button': '💻 Desktop',
                'documents_button': '📁 Documents',
                
                'scan_config': 'Scan Configuration',
                'recursive_scan': 'Recursive scan subdirectories',
                'include_hidden': 'Include hidden files',
                'file_types': 'File types:',
                'max_files': 'Max files:',
                'files_unit': 'files',
                
                'start_scan': '🔍 Start Scan',
                'view_details': '📊 View Details',
                'export_results': '💾 Export Results',
                'clear_results': '🗑️ Clear Results',
                'stop_button': '⏹️ Stop',
                
                'ready_scan': 'Ready to scan',
                'scan_results': 'Scan Results',
                'file_path': '📁 File Path',
                'file_size': '📏 Size',
                'file_type': '📋 Type',
                'file_modified': '📅 Modified',
                'file_extension': '🏷️ Extension',
                
                # Settings
                'general_settings': 'General Settings',
                'language_label': 'Language:',
                'auto_save_settings': 'Auto-save settings on exit',
                'theme_label': 'Theme:',
                'font_size_label': 'Font Size:',
                
                # Status messages
                'scanning': 'Scanning...',
                'processing': 'Processing files...',
                'completed': 'Scan completed',
                'error_occurred': 'An error occurred',
                'no_files_found': 'No files found',
                
                # File types
                'type_all': 'all',
                'type_images': 'images',
                'type_documents': 'documents',
                'type_audio': 'audio',
                'type_video': 'video',
                'type_archives': 'archives',
                'type_code': 'code',
            },
            
            'French': {
                # Window titles
                'main_title': 'MetaCLI - Outil Avancé d\'Extraction de Métadonnées v3.0',
                
                # Menu items
                'menu_file': 'Fichier',
                'menu_edit': 'Édition',
                'menu_tools': 'Outils',
                'menu_view': 'Affichage',
                'menu_help': 'Aide',
                
                'file_open': 'Ouvrir un fichier...',
                'file_open_dir': 'Ouvrir un dossier...',
                'file_export': 'Exporter les résultats...',
                'file_save_report': 'Enregistrer le rapport...',
                'file_recent': 'Fichiers récents',
                'file_exit': 'Quitter',
                
                'edit_copy': 'Copier les résultats',
                'edit_select_all': 'Tout sélectionner',
                'edit_find': 'Rechercher...',
                'edit_filter': 'Filtrer les résultats...',
                
                'tools_batch': 'Traitement par lots...',
                'tools_compare': 'Comparer les fichiers...',
                'tools_report': 'Générer un rapport...',
                'tools_settings': 'Paramètres...',
                'tools_clear_cache': 'Vider le cache',
                
                'view_refresh': 'Actualiser',
                'view_hidden': 'Afficher les fichiers cachés',
                'view_auto_refresh': 'Actualisation automatique',
                'view_expand_all': 'Tout développer',
                'view_collapse_all': 'Tout réduire',
                
                'help_guide': 'Guide utilisateur',
                'help_shortcuts': 'Raccourcis clavier',
                'help_cli': 'Utilisation en ligne de commande',
                'help_updates': 'Vérifier les mises à jour',
                'help_about': 'À propos de MetaCLI',
                
                # Tab titles
                'tab_scanner': '📁 Analyseur de fichiers',
                'tab_metadata': '🔍 Visualiseur de métadonnées',
                'tab_batch': '⚙️ Opérations par lots',
                'tab_settings': '🛠️ Paramètres',
                
                # Scanner tab
                'scanner_title': 'Analyseur de dossiers et fichiers',
                'scanner_subtitle': 'Analyser les dossiers et fichiers pour extraire les métadonnées',
                'target_selection': 'Sélection de la cible',
                'path_label': 'Chemin :',
                'browse_directory': '📁 Parcourir le dossier',
                'select_file': '📄 Sélectionner un fichier',
                'home_button': '🏠 Accueil',
                'desktop_button': '💻 Bureau',
                'documents_button': '📁 Documents',
                
                'scan_config': 'Configuration de l\'analyse',
                'recursive_scan': 'Analyse récursive des sous-dossiers',
                'include_hidden': 'Inclure les fichiers cachés',
                'file_types': 'Types de fichiers :',
                'max_files': 'Fichiers max :',
                'files_unit': 'fichiers',
                
                'start_scan': '🔍 Démarrer l\'analyse',
                'view_details': '📊 Voir les détails',
                'export_results': '💾 Exporter les résultats',
                'clear_results': '🗑️ Effacer les résultats',
                'stop_button': '⏹️ Arrêter',
                
                'ready_scan': 'Prêt à analyser',
                'scan_results': 'Résultats de l\'analyse',
                'file_path': '📁 Chemin du fichier',
                'file_size': '📏 Taille',
                'file_type': '📋 Type',
                'file_modified': '📅 Modifié',
                'file_extension': '🏷️ Extension',
                
                # Settings
                'general_settings': 'Paramètres généraux',
                'language_label': 'Langue :',
                'auto_save_settings': 'Enregistrement automatique des paramètres à la fermeture',
                'theme_label': 'Thème :',
                'font_size_label': 'Taille de police :',
                
                # Status messages
                'scanning': 'Analyse en cours...',
                'processing': 'Traitement des fichiers...',
                'completed': 'Analyse terminée',
                'error_occurred': 'Une erreur s\'est produite',
                'no_files_found': 'Aucun fichier trouvé',
                
                # File types
                'type_all': 'tous',
                'type_images': 'images',
                'type_documents': 'documents',
                'type_audio': 'audio',
                'type_video': 'vidéo',
                'type_archives': 'archives',
                'type_code': 'code',
            },
            
            'Spanish': {
                # Window titles
                'main_title': 'MetaCLI - Herramienta Avanzada de Extracción de Metadatos v3.0',
                
                # Menu items
                'menu_file': 'Archivo',
                'menu_edit': 'Editar',
                'menu_tools': 'Herramientas',
                'menu_view': 'Ver',
                'menu_help': 'Ayuda',
                
                'file_open': 'Abrir archivo...',
                'file_open_dir': 'Abrir directorio...',
                'file_export': 'Exportar resultados...',
                'file_save_report': 'Guardar informe...',
                'file_recent': 'Archivos recientes',
                'file_exit': 'Salir',
                
                'edit_copy': 'Copiar resultados',
                'edit_select_all': 'Seleccionar todo',
                'edit_find': 'Buscar...',
                'edit_filter': 'Filtrar resultados...',
                
                'tools_batch': 'Procesamiento por lotes...',
                'tools_compare': 'Comparar archivos...',
                'tools_report': 'Generar informe...',
                'tools_settings': 'Configuración...',
                'tools_clear_cache': 'Limpiar caché',
                
                'view_refresh': 'Actualizar',
                'view_hidden': 'Mostrar archivos ocultos',
                'view_auto_refresh': 'Actualización automática',
                'view_expand_all': 'Expandir todo',
                'view_collapse_all': 'Contraer todo',
                
                'help_guide': 'Guía del usuario',
                'help_shortcuts': 'Atajos de teclado',
                'help_cli': 'Uso de línea de comandos',
                'help_updates': 'Buscar actualizaciones',
                'help_about': 'Acerca de MetaCLI',
                
                # Tab titles
                'tab_scanner': '📁 Escáner de archivos',
                'tab_metadata': '🔍 Visor de metadatos',
                'tab_batch': '⚙️ Operaciones por lotes',
                'tab_settings': '🛠️ Configuración',
                
                # Scanner tab
                'scanner_title': 'Escáner de directorios y archivos',
                'scanner_subtitle': 'Escanear directorios y archivos para extraer metadatos',
                'target_selection': 'Selección de objetivo',
                'path_label': 'Ruta:',
                'browse_directory': '📁 Explorar directorio',
                'select_file': '📄 Seleccionar archivo',
                'home_button': '🏠 Inicio',
                'desktop_button': '💻 Escritorio',
                'documents_button': '📁 Documentos',
                
                'scan_config': 'Configuración de escaneo',
                'recursive_scan': 'Escaneo recursivo de subdirectorios',
                'include_hidden': 'Incluir archivos ocultos',
                'file_types': 'Tipos de archivo:',
                'max_files': 'Archivos máx:',
                'files_unit': 'archivos',
                
                'start_scan': '🔍 Iniciar escaneo',
                'view_details': '📊 Ver detalles',
                'export_results': '💾 Exportar resultados',
                'clear_results': '🗑️ Limpiar resultados',
                'stop_button': '⏹️ Detener',
                
                'ready_scan': 'Listo para escanear',
                'scan_results': 'Resultados del escaneo',
                'file_path': '📁 Ruta del archivo',
                'file_size': '📏 Tamaño',
                'file_type': '📋 Tipo',
                'file_modified': '📅 Modificado',
                'file_extension': '🏷️ Extensión',
                
                # Settings
                'general_settings': 'Configuración general',
                'language_label': 'Idioma:',
                'auto_save_settings': 'Guardar configuración automáticamente al salir',
                'theme_label': 'Tema:',
                'font_size_label': 'Tamaño de fuente:',
                
                # Status messages
                'scanning': 'Escaneando...',
                'processing': 'Procesando archivos...',
                'completed': 'Escaneo completado',
                'error_occurred': 'Ocurrió un error',
                'no_files_found': 'No se encontraron archivos',
                
                # File types
                'type_all': 'todos',
                'type_images': 'imágenes',
                'type_documents': 'documentos',
                'type_audio': 'audio',
                'type_video': 'video',
                'type_archives': 'archivos',
                'type_code': 'código',
            },
            
            'German': {
                # Window titles
                'main_title': 'MetaCLI - Erweiterte Metadaten-Extraktions-Tool v3.0',
                
                # Menu items
                'menu_file': 'Datei',
                'menu_edit': 'Bearbeiten',
                'menu_tools': 'Werkzeuge',
                'menu_view': 'Ansicht',
                'menu_help': 'Hilfe',
                
                'file_open': 'Datei öffnen...',
                'file_open_dir': 'Verzeichnis öffnen...',
                'file_export': 'Ergebnisse exportieren...',
                'file_save_report': 'Bericht speichern...',
                'file_recent': 'Zuletzt verwendete Dateien',
                'file_exit': 'Beenden',
                
                'edit_copy': 'Ergebnisse kopieren',
                'edit_select_all': 'Alles auswählen',
                'edit_find': 'Suchen...',
                'edit_filter': 'Ergebnisse filtern...',
                
                'tools_batch': 'Stapelverarbeitung...',
                'tools_compare': 'Dateien vergleichen...',
                'tools_report': 'Bericht erstellen...',
                'tools_settings': 'Einstellungen...',
                'tools_clear_cache': 'Cache leeren',
                
                'view_refresh': 'Aktualisieren',
                'view_hidden': 'Versteckte Dateien anzeigen',
                'view_auto_refresh': 'Automatische Aktualisierung',
                'view_expand_all': 'Alle erweitern',
                'view_collapse_all': 'Alle einklappen',
                
                'help_guide': 'Benutzerhandbuch',
                'help_shortcuts': 'Tastenkürzel',
                'help_cli': 'Kommandozeilen-Nutzung',
                'help_updates': 'Nach Updates suchen',
                'help_about': 'Über MetaCLI',
                
                # Tab titles
                'tab_scanner': '📁 Datei-Scanner',
                'tab_metadata': '🔍 Metadaten-Viewer',
                'tab_batch': '⚙️ Stapeloperationen',
                'tab_settings': '🛠️ Einstellungen',
                
                # Scanner tab
                'scanner_title': 'Verzeichnis- und Datei-Scanner',
                'scanner_subtitle': 'Verzeichnisse und Dateien scannen, um Metadaten zu extrahieren',
                'target_selection': 'Zielauswahl',
                'path_label': 'Pfad:',
                'browse_directory': '📁 Verzeichnis durchsuchen',
                'select_file': '📄 Datei auswählen',
                'home_button': '🏠 Startseite',
                'desktop_button': '💻 Desktop',
                'documents_button': '📁 Dokumente',
                
                'scan_config': 'Scan-Konfiguration',
                'recursive_scan': 'Rekursives Scannen von Unterverzeichnissen',
                'include_hidden': 'Versteckte Dateien einschließen',
                'file_types': 'Dateitypen:',
                'max_files': 'Max. Dateien:',
                'files_unit': 'Dateien',
                
                'start_scan': '🔍 Scan starten',
                'view_details': '📊 Details anzeigen',
                'export_results': '💾 Ergebnisse exportieren',
                'clear_results': '🗑️ Ergebnisse löschen',
                'stop_button': '⏹️ Stoppen',
                
                'ready_scan': 'Bereit zum Scannen',
                'scan_results': 'Scan-Ergebnisse',
                'file_path': '📁 Dateipfad',
                'file_size': '📏 Größe',
                'file_type': '📋 Typ',
                'file_modified': '📅 Geändert',
                'file_extension': '🏷️ Erweiterung',
                
                # Settings
                'general_settings': 'Allgemeine Einstellungen',
                'language_label': 'Sprache:',
                'auto_save_settings': 'Einstellungen beim Beenden automatisch speichern',
                'theme_label': 'Design:',
                'font_size_label': 'Schriftgröße:',
                
                # Status messages
                'scanning': 'Scannen...',
                'processing': 'Dateien verarbeiten...',
                'completed': 'Scan abgeschlossen',
                'error_occurred': 'Ein Fehler ist aufgetreten',
                'no_files_found': 'Keine Dateien gefunden',
                
                # File types
                'type_all': 'alle',
                'type_images': 'Bilder',
                'type_documents': 'Dokumente',
                'type_audio': 'Audio',
                'type_video': 'Video',
                'type_archives': 'Archive',
                'type_code': 'Code',
            }
        }
    
    def get_text(self, key: str, default: str = None) -> str:
        """Get translated text for the given key."""
        if self.current_language in self.translations:
            return self.translations[self.current_language].get(key, default or key)
        return self.translations['English'].get(key, default or key)
    
    def set_language(self, language: str):
        """Set the current language."""
        if language in self.translations:
            self.current_language = language
    
    def get_available_languages(self) -> list:
        """Get list of available languages."""
        return list(self.translations.keys())

# Global translation manager instance
_translation_manager = None

def get_translation_manager() -> TranslationManager:
    """Get the global translation manager instance."""
    global _translation_manager
    if _translation_manager is None:
        _translation_manager = TranslationManager()
    return _translation_manager

def t(key: str, default: str = None) -> str:
    """Shorthand function to get translated text."""
    return get_translation_manager().get_text(key, default)

def set_language(language: str):
    """Set the current language for translations."""
    get_translation_manager().set_language(language)

def get_available_languages() -> list:
    """Get list of available languages."""
    return get_translation_manager().get_available_languages()