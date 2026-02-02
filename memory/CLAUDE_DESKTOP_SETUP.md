# Configuration Claude.ai Desktop pour Claude Brain

## 📋 Résumé

Claude.ai Desktop utilise maintenant le **même système de mémoire** que Claude Code CLI via MCP (Model Context Protocol).

## ✅ Configuration Terminée

La configuration a été automatiquement ajoutée à :
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

## 🚀 Démarrage Rapide

### 1. Démarrer le Service Mémoire (Requis)

Le service de mémoire doit être démarré **AVANT** d'utiliser Claude Desktop :

```bash
cd ~/.claude/memory
docker compose up -d
```

**Vérification :**
```bash
curl http://localhost:8100/health
```

Devrait afficher : `"status": "healthy"`

### 2. Redémarrer Claude Desktop

Fermez complètement Claude.ai Desktop et relancez-le pour charger la configuration MCP.

**⚠️ Important :** Utilisez **Cmd+Q** pour quitter complètement l'application (pas juste fermer la fenêtre).

### 3. Vérifier la Connexion MCP

Dans Claude Desktop, vous devriez voir les mêmes outils de mémoire disponibles :

- 🔍 `search_memory` - Rechercher dans les souvenirs
- 💾 `store_memory` - Sauvegarder un souvenir
- 📊 `get_context` - Obtenir le contexte récent
- 🔗 `link_memories` - Lier des souvenirs
- ✅ `mark_resolved` - Marquer une erreur comme résolue
- Et tous les autres outils...

## 🎯 Utilisation

### Workflow Identique CLI et Desktop

**1. Rechercher dans la mémoire :**
```
"Recherche ce qu'on a fait sur le dashboard"
```

Claude Desktop utilisera `search_memory()` automatiquement.

**2. Sauvegarder des connaissances :**
```
"Sauvegarde cette solution pour référence future"
```

Claude Desktop utilisera `store_memory()` automatiquement.

**3. Qualité Automatique :**

Même validation de qualité qu'en CLI :
- ✅ Minimum 30 caractères
- ✅ Minimum 2 tags
- ✅ Minimum 5 mots
- ✅ Validation type-spécifique (décisions = rationale requis, erreurs = solution requise)

## 📊 Dashboard Web (Optionnel)

Le dashboard web est accessible depuis les deux environnements :

**URL :** http://localhost:8100

**Fonctionnalités :**
- 📈 Visualisation des souvenirs
- 🔍 Recherche avancée
- 📊 Analytics et métriques
- 🧠 Advanced Brain Metrics
- 🌐 Knowledge Graph

## ⚙️ Configuration Avancée

### Ajouter d'Autres Serveurs MCP

Éditez `~/Library/Application Support/Claude/claude_desktop_config.json` :

```json
{
  "mcpServers": {
    "memory": {
      "command": "node",
      "args": ["/Users/h4ckm1n/.claude/mcp/memory-mcp/dist/index.js"],
      "env": {
        "MEMORY_API_URL": "http://localhost:8100"
      }
    },
    "autre-serveur": {
      "command": "...",
      "args": ["..."]
    }
  }
}
```

### Variables d'Environnement

Le serveur MCP utilise :
```
MEMORY_API_URL=http://localhost:8100
```

Pour changer le port ou l'hôte, modifiez cette variable dans la config.

## 🔧 Dépannage

### Problème : Claude Desktop ne voit pas les outils

**Solution :**
1. Vérifiez que le service tourne : `curl http://localhost:8100/health`
2. Redémarrez Claude Desktop (Cmd+Q puis relancez)
3. Vérifiez les logs : `docker compose -f ~/.claude/memory/docker-compose.yml logs`

### Problème : "Connection refused"

**Solution :**
```bash
cd ~/.claude/memory
docker compose restart
```

### Problème : Service n'a pas démarré

**Solution :**
```bash
cd ~/.claude/memory
docker compose up -d
docker compose ps  # Vérifier le statut
```

### Voir les Logs du Service

```bash
# Logs du service mémoire
docker compose -f ~/.claude/memory/docker-compose.yml logs -f claude-mem-service

# Logs de Qdrant
docker compose -f ~/.claude/memory/docker-compose.yml logs -f qdrant

# Logs de Neo4j
docker compose -f ~/.claude/memory/docker-compose.yml logs -f neo4j
```

## 📝 Différences CLI vs Desktop

| Fonctionnalité | CLI | Desktop | Note |
|----------------|-----|---------|------|
| Mémoire partagée | ✅ | ✅ | Même base de données |
| Qualité enforcement | ✅ | ✅ | Même validation |
| Dashboard web | ✅ | ✅ | http://localhost:8100 |
| Hooks automatiques | ✅ | ❌ | CLI seulement |
| Agents spécialisés | ✅ | ❌ | CLI seulement |
| MCP tools | ✅ | ✅ | Via configuration |

## 🎨 Dashboard Dark Theme

Le dashboard utilise le nouveau thème sombre moderne avec :
- Gradient effects
- Glassmorphism
- Color-coded metrics (blue/purple/emerald/rose)
- Always-visible Advanced Analytics

## 🔄 Synchronisation

**Les deux environnements partagent :**
- ✅ Base de données de souvenirs (Qdrant)
- ✅ Knowledge graph (Neo4j)
- ✅ Documents indexés
- ✅ Métriques et analytics

**Workflow recommandé :**
1. Utilisez **Claude Code CLI** pour le développement complexe
2. Utilisez **Claude Desktop** pour les questions rapides et recherche
3. Les deux accèdent à la même mémoire !

## 🚦 Statut du Service

**Vérifier rapidement :**
```bash
# Health check
curl -s http://localhost:8100/health | jq '.status'

# Nombre de souvenirs
curl -s http://localhost:8100/health | jq '.memory_count'

# Statut des services
cd ~/.claude/memory && docker compose ps
```

## 💡 Tips

1. **Toujours démarrer le service avant d'utiliser Claude Desktop**
2. **Redémarrer l'app après modification de la config MCP**
3. **Utiliser le dashboard web pour visualiser et gérer les souvenirs**
4. **Les souvenirs sont partagés entre CLI et Desktop**
5. **Les hooks automatiques sont uniquement en CLI**

## 📚 Documentation Complète

- README principal : `~/.claude/memory/README.md`
- Guide mémoire : `~/.claude/memory/MEMORY_WORKFLOW.md`
- Troubleshooting : `~/.claude/memory/TROUBLESHOOTING.md`
- Quick Start : `~/.claude/memory/QUICK_START.md`

## 🔗 Liens Utiles

- Dashboard : http://localhost:8100
- Health Check : http://localhost:8100/health
- API Docs : http://localhost:8100/docs (si activé)
- Knowledge Graph : http://localhost:8100 (section Graph)

## ✨ Prochaines Étapes

1. Redémarrez Claude Desktop (Cmd+Q puis relancer)
2. Testez avec : "Recherche tous les souvenirs sur le dashboard"
3. Explorez le dashboard web : http://localhost:8100
4. Créez votre premier souvenir depuis Desktop !

---

**Configuration créée le :** 2026-02-01
**Version :** 1.0.0
**Système :** Claude Brain Memory System
