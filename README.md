# Dynamic Proof Research Engine

Progetto di **Alessio Mattoccia**.

**Dynamics Lab · Engine 03 · v0.1.0**

Motore locale di ricerca deduttiva con registro SQLite, orchestratore persistente e dashboard. Registra domini, ipotesi, provenienza e dipendenze. Combina calcolo simbolico, intervalli certificati, ricerca di controesempi e verifiche formali opzionali.

| Laboratorio | Esperimenti inclusi |
| --- | --- |
| Riemann e teoria dei numeri | Criterio di Robin, riduzione per divisibilità, controlli finiti con Arb e zeri indicizzati della zeta. |
| Teoria delle stringhe | Integrale toroidale di genere uno, dualità T, termine costante e proiezioni modulari. |
| TMF · Geometria multiscala | Connessioni di Levi-Civita, controesempio DPR-003, riduzione monoscala e azioni con pesi variabili. |

La TMF è trattata come teoria candidata. Le verifiche di Robin sono riferite ai domini dei singoli rapporti. L’ipotesi di Riemann resta aperta. [Pagina del motore e rapporti](https://mattoccia.com/dynamics-lab/dynamic-proof/) · [Clay Mathematics Institute](https://www.claymath.org/millennium/riemann-hypothesis/)

## Avvio

Ambiente verificato su macOS Apple Silicon con Python 3.12. Esegui questi comandi dalla cartella estratta o dal checkout.

~~~sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m dynamic_proof serve
~~~

Apri la [dashboard locale](http://127.0.0.1:8791/). Al primo avvio il motore crea `state/`, registra i tre laboratori e comincia i calcoli. `Ctrl+C` interrompe il processo. La ripresa usa lo stesso registro.

~~~sh
.venv/bin/python -m dynamic_proof status
.venv/bin/python -m dynamic_proof control paused
.venv/bin/python -m dynamic_proof control running
.venv/bin/python -m dynamic_proof control stopped
~~~

`config.toml` controlla il budget per esperimento, la cadenza, la porta e le ricerche bibliografiche. La configurazione distribuita usa il catalogo locale. `online_literature = true` abilita interrogazioni pubbliche su arXiv e Crossref con i termini dei laboratori. Per avviare un registro separato, usa `--state` prima del sottocomando.

~~~sh
.venv/bin/python -m dynamic_proof --state .work/demo run --cycles 8
.venv/bin/python -m dynamic_proof queue riemann sources/example-statement.json
~~~

Il comando `queue` accetta enunciati strutturati. Nel frammento lineare intero il motore usa SMT per cercare controesempi e, con Lean configurato, tenta la verifica formale. La modalità `relax` propone varianti che rimuovono un’ipotesi per volta. Su macOS è disponibile il servizio facoltativo `.venv/bin/python scripts/macos_service.py install`, con log nel registro della copia che lo installa.

## Riproduzione e test

L’archivio include i dati pubblici DPR-001, DPR-002 e DPR-003, i manifest con SHA-256 e lo script di replay. I file corrispondono alle versioni distribuite dal sito. [Indice pubblico degli esperimenti](https://mattoccia.com/dynamics-lab/dynamic-proof/PUBLIC_EXPORT.json)

~~~sh
.venv/bin/python experiments/verify-dynamic-proof.py.txt
.venv/bin/python -m unittest discover -s tests -v
~~~

Il primo comando ricalcola i tre risultati dal pacchetto. La suite esercita il nucleo, le verifiche scientifiche, la dashboard e il recupero dopo interruzione. I test specifici di Lean si attivano quando è presente la toolchain.

### Verifica formale opzionale

Posiziona Lean **4.33.1** con `bin/lean` e `bin/lake` in `.tools/lean` oppure collega lì la cartella della distribuzione ufficiale. Da `proofs/` carica le dipendenze fissate nel manifest.

~~~sh
cd proofs
PATH="$PWD/../.tools/lean/bin:$PATH" lake exe cache get Mathlib.Tactic.Ring Mathlib.Tactic.NormNum Mathlib.Data.Rat.Defs
cd ..
.venv/bin/python -m unittest discover -s tests -v
~~~

Il kernel controlla i tipi attesi e gli assiomi delle dichiarazioni. Il rapporto distingue le identità formalizzate dalle prove analitiche, dai risultati riportati nelle fonti e dalle verifiche numeriche. [Distribuzione ufficiale di Lean 4.33.1](https://github.com/leanprover/lean4/releases/tag/v4.33.1)

## Licenza

I sorgenti originali e i materiali di riproduzione inclusi sono distribuiti sotto **Apache License 2.0**. Le dipendenze si installano separatamente e mantengono le loro licenze. Le fonti scientifiche sono citate nei rispettivi rapporti. [LICENSE](LICENSE) · [NOTICE](NOTICE) · [Licenze delle dipendenze](THIRD_PARTY_NOTICES.md)
