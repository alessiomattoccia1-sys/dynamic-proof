# Particle Theory

Quarto laboratorio di Dynamic Proof Research Engine. Usa il catalogo `Lab`, il Runner, il registro SQLite, le classi di evidenza e i rapporti del Core. Il primo programma studia fermioni di Weyl sinistrorsi con cariche intere in un settore U(1) isolato e masse da Yukawa rinormalizzabili.

## Avvio

Esegui dal checkout con Python 3.12 e le dipendenze del repository.

~~~sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m dynamic_proof --state .local/particle-research init --lab particle_theory
.venv/bin/python -m dynamic_proof --state .local/particle-research run --lab particle_theory --cycles 30
.venv/bin/python -m dynamic_proof --state .local/particle-research status
.venv/bin/python -m dynamic_proof --state .local/particle-research serve --lab particle_theory --port 8791
~~~

La dashboard è accessibile in loopback. La scheda Particle Theory mostra il problema attivo, gli esiti, l'avanzamento in unità di ricerca e le matrici. Le schede degli enunciati aprono le dipendenze nel registro. [Dashboard locale](http://127.0.0.1:8791/)

## Problemi JSON

~~~sh
.venv/bin/python -m dynamic_proof --state .local/particle-research submit particle_theory experiments/particle/PT-006.json
.venv/bin/python -m dynamic_proof --state .local/particle-research run --lab particle_theory --cycles 10
~~~

| Chiave | Valori e significato |
| --- | --- |
| `id`, `title` | Identificativo e titolo del problema. |
| `type` | `classification`, `construction`, `counterexample` oppure `proof`. |
| `fermions`, `charge_bound` | Numero di fermioni fra 1 e 10. Limite assoluto da 1 a 32. La carica zero è esclusa. Nei problemi di prova determinano il dominio della ricerca di controesempi. |
| `fermion_charges` | Vettore fissato opzionale. Permutazioni e inversione globale identificano lo stesso input. |
| `anomalies` | Per impostazione predefinita `["linear","cubic"]`. Si possono scegliere sottoinsiemi per studiare le singole condizioni. |
| `strict_chirality`, `primitive` | Entrambi `true` per impostazione predefinita. Controllano rispettivamente coppie opposte e MCD unitario. |
| `scalar_charges` | Lista opzionale di cariche intere non nulle. Lo scalare e il coniugato danno lo stesso supporto. Se omessa, il pool è costituito da tutte le somme assolute non nulle delle coppie fermioniche. |
| `max_scalars`, `mass_condition` | Numero massimo di cariche scalari distinte. `full_rank` richiede un testimone invertibile. `any` ammette ogni rango. Con `any` e limite zero si eseguono solo i controlli fermionici. |
| `method` | `enumeration` percorre tutti i multinsiemi. `quadratic` usa la riduzione sulle ultime due cariche e richiede entrambe le condizioni di anomalia. |
| `theorem` | Nei problemi `proof`, `odd_scalar_valuation`, `two_scalar_labels` oppure `one_scalar_multiple_four`. Le ipotesi universali sono quelle dell'enunciato. Nei problemi `counterexample` si cerca una confutazione della sufficienza aritmetica con l'insieme di scalari fissato. |
| `completeness` | `exhaustive` per classificazione e prova. `witness` per confutazione. La costruzione accetta entrambi. |
| `references` | Identificativi bibliografici del catalogo Particle Theory. I lavori di Costa, Dobrescu e Fox sono inclusi nella provenienza. |
| `budget` | `steps_per_cycle`, `max_steps`, `max_models`, `smt_ms`, `verification_steps` e `scalar_sets`. Durata, CPU, RAM e quota giornaliera sono nel TOML del Runner. |

La coda registra l'input normalizzato. Ripresentare lo stesso problema con cariche permutate o invertite e gli stessi altri campi produce la stessa chiave di lavoro. Ogni checkpoint conserva le classi trovate e il cursore della successiva fetta. In caso di interruzione, la fetta corrente può essere ricalcolata a partire dall'ultimo checkpoint.

## Programma

- **PT-001** riproduce il dominio del pilot. **PT-002** controlla tutti i supporti a uno scalare e costruisce un testimone di massa a due scalari.
- **PT-003** verifica il teorema di parità su matrici di dimensione arbitraria. **PT-004** aumenta il numero di fermioni e il limite assoluto.
- **PT-005** valuta simultaneamente chiralità, anomalie e rango pieno con un pool scalare fissato. **PT-006** cerca il limite della condizione aritmetica necessaria.
- **PT-007** ricava un vincolo su rapporti scalari e numero dispari di fermioni. **PT-008** misura il caso finito senza soluzioni a quattro fermioni.
- **PT-009** esplora il settore dispari successivo. **PT-010** verifica se i modelli a sei fermioni trovati nel dominio scelto ammettono massa piena con un solo scalare.
- **PT-011** dimostra la divisibilità di \(n\) per quattro sotto l'ipotesi sui punti fissi delle due riflessioni di carica. **PT-012** costruisce un modello a otto fermioni con rango pieno usando due somme di due quadrati uguali.

Le restrizioni del programma sono dichiarate nei file prima dell'esecuzione. PT-005 testa il pool 1–6 per contenere il numero di supporti. PT-006 mantiene il rapporto scalare 1:2 e ne varia la scala rispetto all'esempio di riferimento. PT-010 verifica il caso pari in cui l'argomento di parità di PT-003 lascia aperta l'invertibilità.

[Metodo scientifico](SCIENTIFIC_METHOD.md) · [Risultati](RESULTS.md) · [Riproducibilità](REPRODUCIBILITY.md) · [Letteratura](PRIOR_ART.md) · [Limiti](LIMITATIONS.md)
