// What the documentation page adds to each section of content.js / content.fr.js:
// an icon, a one-line summary and the screenshots (public/docs/<language>/<name>.png, made by
// src/ui/scripts/screenshots/capture.py). A screenshot that does not exist is not displayed.

export default {
  overview: {
    icon: "dashboard",
    summary: {
      en: "What BackROLL does and how the pieces fit together.",
      fr: "Ce que fait BackROLL et comment les éléments s'articulent.",
    },
    figures: [{ name: "dashboard", caption: { en: "The dashboard", fr: "Le tableau de bord" } }],
  },
  "first-steps": {
    icon: "play_circle",
    summary: {
      en: "From a new installation to a first backup, in order.",
      fr: "D'une installation neuve à une première sauvegarde, dans l'ordre.",
    },
    figures: [],
  },
  users: {
    icon: "people",
    summary: {
      en: "Three roles, lock after failed logins, and the user page.",
      fr: "Trois rôles, blocage après des échecs de connexion, et la page des utilisateurs.",
    },
    figures: [{ name: "users", caption: { en: "Parameters > Users", fr: "Paramètres > Utilisateurs" } }],
  },
  directory: {
    icon: "domain",
    summary: {
      en: "Log in with the Active Directory, a role for each group, and the logs.",
      fr: "Se connecter avec l'Active Directory, un rôle pour chaque groupe, et le journal.",
    },
    figures: [{ name: "directory", caption: { en: "Parameters > Active Directory", fr: "Paramètres > Active Directory" } }],
  },
  storage: {
    icon: "storage",
    summary: {
      en: "Where the backups are written.",
      fr: "L'endroit où les sauvegardes sont écrites.",
    },
    figures: [{ name: "storage", caption: { en: "Configuration > Storage", fr: "Configuration > Stockage" } }],
  },
  connectors: {
    icon: "cloud",
    summary: {
      en: "The access to a CloudStack environment.",
      fr: "L'accès à un environnement CloudStack.",
    },
    figures: [{ name: "connectors", caption: { en: "Configuration > Connectors", fr: "Configuration > Connecteurs" } }],
  },
  hypervisors: {
    icon: "dns",
    summary: {
      en: "KVM hosts and the pools that group them.",
      fr: "Les hôtes KVM et les pools qui les regroupent.",
    },
    figures: [
      { name: "hypervisors", caption: { en: "Resources > Hypervisors", fr: "Ressources > Hyperviseurs" } },
      { name: "pools", caption: { en: "Resources > Pools", fr: "Ressources > Pools" } },
    ],
  },
  policies: {
    icon: "schedule",
    summary: {
      en: "When to back up, how long to keep, where and what.",
      fr: "Quand sauvegarder, combien de temps conserver, où et quoi.",
    },
    figures: [
      { name: "policies", caption: { en: "The list of policies", fr: "La liste des politiques" } },
      { name: "policy-form", caption: { en: "Editing a policy: retention and folders", fr: "Modifier une politique : rétention et dossiers" } },
    ],
  },
  folders: {
    icon: "folder",
    summary: {
      en: "Save folders on their own and get a single file back.",
      fr: "Sauvegarder des dossiers à part et retrouver un seul fichier.",
    },
    figures: [
      { name: "virtual-machine", caption: { en: "The archives of folders are labelled FILES", fr: "Les archives de dossiers sont étiquetées FILES" } },
    ],
  },
  hooks: {
    icon: "notifications",
    summary: {
      en: "Slack notifications of the backup results.",
      fr: "Notifications Slack du résultat des sauvegardes.",
    },
    figures: [{ name: "external-hooks", caption: { en: "Configuration > External hooks", fr: "Configuration > Hooks externes" } }],
  },
  backups: {
    icon: "backup",
    summary: {
      en: "Scheduled and manual backups, simultaneous backups, tasks.",
      fr: "Sauvegardes planifiées et manuelles, sauvegardes simultanées, tâches.",
    },
    figures: [
      { name: "kickstart", caption: { en: "Tasks > Task kickstart", fr: "Tâches > Lancement de tâche" } },
      {
        name: "dashboard-attention",
        caption: {
          en: "Dashboard: a machine whose backups are stopped, and the button that resumes them",
          fr: "Tableau de bord : une machine dont les sauvegardes sont arrêtées, et le bouton qui les reprend",
        },
      },
      { name: "tasks-backup", caption: { en: "Tasks > Backup", fr: "Tâches > Sauvegarde" } },
      { name: "settings", caption: { en: "Parameters > Settings", fr: "Paramètres > Réglages" } },
    ],
  },
  cleanup: {
    icon: "delete_sweep",
    summary: {
      en: "Delete old backups and the backups of deleted machines, with a log.",
      fr: "Supprimer les anciennes sauvegardes et celles des machines disparues, avec un journal.",
    },
    figures: [{ name: "cleanup", caption: { en: "Tasks > Clean backup", fr: "Tâches > Nettoyage des sauvegardes" } }],
  },
  restore: {
    icon: "restore",
    summary: {
      en: "A file, a disk, or a whole machine.",
      fr: "Un fichier, un disque, ou une machine entière.",
    },
    figures: [
      { name: "virtual-machine", caption: { en: "The backups of a virtual machine", fr: "Les sauvegardes d'une machine virtuelle" } },
      { name: "backup-files", caption: { en: "Browsing the files of a backup", fr: "Parcourir les fichiers d'une sauvegarde" } },
    ],
  },
  drp: {
    icon: "settings_backup_restore",
    summary: {
      en: "Rebuild a machine as a new CloudStack machine, with a history.",
      fr: "Reconstruire une machine en nouvelle machine CloudStack, avec un historique.",
    },
    figures: [{ name: "drp", caption: { en: "Tasks > Disaster recovery", fr: "Tâches > Reprise après sinistre" } }],
  },
  audit: {
    icon: "history",
    summary: {
      en: "Who did what, and when.",
      fr: "Qui a fait quoi, et quand.",
    },
    figures: [{ name: "audit-log", caption: { en: "Parameters > Audit log", fr: "Paramètres > Journal d'audit" } }],
  },
  interface: {
    icon: "tune",
    summary: {
      en: "Refresh, language and the dashboard.",
      fr: "Actualisation, langue et tableau de bord.",
    },
    figures: [{ name: "topbar", caption: { en: "The top bar and its refresh control", fr: "La barre du haut et son actualisation" } }],
  },
  config: {
    icon: "settings",
    summary: {
      en: "Environment variables and updating.",
      fr: "Variables d'environnement et mise à jour.",
    },
    figures: [],
  },
  troubleshooting: {
    icon: "build",
    summary: {
      en: "Symptoms, causes and fixes.",
      fr: "Symptômes, causes et solutions.",
    },
    figures: [],
  },
  limits: {
    icon: "block",
    summary: {
      en: "What BackROLL does not do (yet).",
      fr: "Ce que BackROLL ne fait pas (encore).",
    },
    figures: [],
  },
};

// The cards of the welcome area: the four things people come for.
export const quickStart = [
  { id: "first-steps", icon: "play_circle", color: "primary" },
  { id: "policies", icon: "schedule", color: "info" },
  { id: "restore", icon: "restore", color: "success" },
  { id: "drp", icon: "settings_backup_restore", color: "warning" },
];
