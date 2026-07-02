# Limites Albert — relevé `make probe` (S1.5)

Relevé du 2026-07-02 18:34 UTC sur `https://albert.api.etalab.gouv.fr/v1`. Fichier généré — ne pas éditer.

## Statut des relevés

- **modeles** : ok
- **quotas** : ok
- **chat** : ok
- **embeddings** : ok

## Modèles servis (GET /v1/models)

| id | type | aliases | max_context_length | owned_by |
|---|---|---|---|---|
| openai/gpt-oss-120b | text-generation | ['openweight-large'] | 131072 | Services du premier ministre - DINUM |
| Qwen/Qwen3-Coder-30B-A3B-Instruct | text-generation | ['openweight-code'] | 262144 | Services du premier ministre - DINUM |
| mistralai/Ministral-3-8B-Instruct-2512 | image-text-to-text | ['openweight-small'] | 262144 | Services du premier ministre - DINUM |
| BAAI/bge-m3 | text-embeddings-inference | ['openweight-embeddings'] | 8192 | Services du premier ministre - DINUM |
| BAAI/bge-reranker-v2-m3 | text-classification | ['openweight-rerank'] | 8192 | Services du premier ministre - DINUM |
| mistralai/Mistral-Small-3.2-24B-Instruct-2506 | image-text-to-text | ['openweight-medium', 'albert-large'] | 128000 | Services du premier ministre - DINUM |
| openai/whisper-large-v3 | automatic-speech-recognition | ['openweight-audio'] | None | Services du premier ministre - DINUM |

<details><summary>Réponse complète</summary>

```json
[
  {
    "id": "openai/gpt-oss-120b",
    "created": 1765375160,
    "object": "model",
    "owned_by": "Services du premier ministre - DINUM",
    "type": "text-generation",
    "aliases": [
      "openweight-large"
    ],
    "max_context_length": 131072,
    "costs": {
      "prompt_tokens": 0.0,
      "completion_tokens": 0.0
    }
  },
  {
    "id": "Qwen/Qwen3-Coder-30B-A3B-Instruct",
    "created": 1765384283,
    "object": "model",
    "owned_by": "Services du premier ministre - DINUM",
    "type": "text-generation",
    "aliases": [
      "openweight-code"
    ],
    "max_context_length": 262144,
    "costs": {
      "prompt_tokens": 0.0,
      "completion_tokens": 0.0
    }
  },
  {
    "id": "mistralai/Ministral-3-8B-Instruct-2512",
    "created": 1765384336,
    "object": "model",
    "owned_by": "Services du premier ministre - DINUM",
    "type": "image-text-to-text",
    "aliases": [
      "openweight-small"
    ],
    "max_context_length": 262144,
    "costs": {
      "prompt_tokens": 0.0,
      "completion_tokens": 0.0
    }
  },
  {
    "id": "BAAI/bge-m3",
    "created": 1765384417,
    "object": "model",
    "owned_by": "Services du premier ministre - DINUM",
    "type": "text-embeddings-inference",
    "aliases": [
      "openweight-embeddings"
    ],
    "max_context_length": 8192,
    "costs": {
      "prompt_tokens": 0.0,
      "completion_tokens": 0.0
    }
  },
  {
    "id": "BAAI/bge-reranker-v2-m3",
    "created": 1765384523,
    "object": "model",
    "owned_by": "Services du premier ministre - DINUM",
    "type": "text-classification",
    "aliases": [
      "openweight-rerank"
    ],
    "max_context_length": 8192,
    "costs": {
      "prompt_tokens": 0.0,
      "completion_tokens": 0.0
    }
  },
  {
    "id": "mistralai/Mistral-Small-3.2-24B-Instruct-2506",
    "created": 1765979887,
    "object": "model",
    "owned_by": "Services du premier ministre - DINUM",
    "type": "image-text-to-text",
    "aliases": [
      "openweight-medium",
      "albert-large"
    ],
    "max_context_length": 128000,
    "costs": {
      "prompt_tokens": 0.0,
      "completion_tokens": 0.0
    }
  },
  {
    "id": "openai/whisper-large-v3",
    "created": 1778071574,
    "object": "model",
    "owned_by": "Services du premier ministre - DINUM",
    "type": "automatic-speech-recognition",
    "aliases": [
      "openweight-audio"
    ],
    "max_context_length": null,
    "costs": {
      "prompt_tokens": 0.0,
      "completion_tokens": 0.0
    }
  }
]
```

</details>

## Quotas du compte (GET /v1/me/info — objet `limits`)

```json
{
  "limits": [
    {
      "router_id": 342,
      "type": "rpm",
      "value": 500
    },
    {
      "router_id": 342,
      "type": "rpd",
      "value": 50000
    },
    {
      "router_id": 342,
      "type": "tpm",
      "value": null
    },
    {
      "router_id": 342,
      "type": "tpd",
      "value": null
    },
    {
      "router_id": 343,
      "type": "rpm",
      "value": 500
    },
    {
      "router_id": 343,
      "type": "rpd",
      "value": 50000
    },
    {
      "router_id": 343,
      "type": "tpm",
      "value": null
    },
    {
      "router_id": 343,
      "type": "tpd",
      "value": null
    },
    {
      "router_id": 338,
      "type": "rpm",
      "value": 50
    },
    {
      "router_id": 338,
      "type": "rpd",
      "value": 1000
    },
    {
      "router_id": 338,
      "type": "tpm",
      "value": 128000
    },
    {
      "router_id": 338,
      "type": "tpd",
      "value": 2460000
    },
    {
      "router_id": 339,
      "type": "rpm",
      "value": 50
    },
    {
      "router_id": 339,
      "type": "rpd",
      "value": 1000
    },
    {
      "router_id": 339,
      "type": "tpm",
      "value": 128000
    },
    {
      "router_id": 339,
      "type": "tpd",
      "value": 2459999
    },
    {
      "router_id": 420,
      "type": "rpm",
      "value": 50
    },
    {
      "router_id": 420,
      "type": "rpd",
      "value": 1000
    },
    {
      "router_id": 420,
      "type": "tpm",
      "value": 128000
    },
    {
      "router_id": 420,
      "type": "tpd",
      "value": 2460000
    },
    {
      "router_id": 337,
      "type": "rpm",
      "value": 10
    },
    {
      "router_id": 337,
      "type": "rpd",
      "value": 1000
    },
    {
      "router_id": 337,
      "type": "tpm",
      "value": 128000
    },
    {
      "router_id": 337,
      "type": "tpd",
      "value": 1280000
    },
    {
      "router_id": 1085,
      "type": "rpm",
      "value": 50
    },
    {
      "router_id": 1085,
      "type": "rpd",
      "value": 1000
    },
    {
      "router_id": 1085,
      "type": "tpm",
      "value": null
    },
    {
      "router_id": 1085,
      "type": "tpd",
      "value": null
    }
  ]
}
```

## Appel de chat minimal

- alias_demande : `openweight-large`
- modele_resolu : `openweight-large`
- reponse : `OK`
- finish_reason : `stop`
- latence_s : `0.27`

## Appel d'embeddings minimal

- alias_demande : `openweight-embeddings`
- modele_resolu : `openweight-embeddings`
- dimension : `1024`
- latence_s : `0.06`
