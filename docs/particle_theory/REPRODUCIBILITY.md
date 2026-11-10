# Riproducibilità

La baseline Git è `fd2512333d903467a34dd4eae048ea3429faaf8c`, con ultimo rilascio `v0.1.0` al commit `42d04e95c5cd7c44befda4aacb976fe0a0064167`. Lo sviluppo usa il worktree `codex/particle-theory` collegato al repository originale sul Mac mini. [Repository](https://github.com/alessiomattoccia1-sys/dynamic-proof)

Il file `Dynamic_Proof_Particle_Pilot.zip` non era presente nelle cartelle di lavoro, di download e degli allegati ispezionate. I test ricostruiscono la baseline dai dati della specifica e da un'enumerazione indipendente eseguita prima delle modifiche. Per \((-9,-5,-1,7,8)\), le somme lineare e cubica sono zero. I due orientamenti di segno costituiscono una sola classe fra 26.334 multinsiemi. La matrice per \(h=(1,2)\) ha determinante \(b^2c^2d\). Ponendo \(a=b=c=d=1\) il determinante è 1.

~~~sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python experiments/verify-dynamic-proof.py.txt
.venv/bin/python -m dynamic_proof --state .local/particle-research init --lab particle_theory
.venv/bin/python -m dynamic_proof --state .local/particle-research run --lab particle_theory --cycles 30
~~~

Per la verifica formale, usa Lean 4.33.1 e il commit mathlib fissato in `proofs/lake-manifest.json`. Con il binario in `.tools/lean/bin` e le dipendenze Lake presenti, il test `test_no_go_full_lean_statement` controlla tipi, hash della fonte e assiomi delle due dichiarazioni. Il rapporto distingue le prove formali dall'evidenza analitica e dai controlli finiti.

~~~sh
cd proofs
PATH="$PWD/../.tools/lean/bin:$PATH" lake env lean --trust=0 ParticleNoGo.lean
~~~

Il registro `research.sqlite3` contiene i tentativi, le transazioni di checkpoint, gli artefatti, le dipendenze e le valutazioni bibliografiche. `reports/` contiene JSON e Markdown per ogni tentativo concluso e bozze LaTeX per le derivazioni con fascicolo. Compila le bozze con XeLaTeX. Il digest dell'input normalizzato e le versioni delle librerie compaiono nei rapporti.

Nel worktree di qualifica sul Mac mini è già disponibile l'interprete `../dynamic-proof/.venv/bin/python`. Dal worktree, questi comandi consultano il registro eseguito e aprono la relativa dashboard.

~~~sh
../dynamic-proof/.venv/bin/python -B -m dynamic_proof --state .local/particle-research status
../dynamic-proof/.venv/bin/python -B -m dynamic_proof --state .local/particle-research serve --lab particle_theory --port 8791
~~~

La configurazione salvata in `.local/particle-research/research.toml` abilita i tre canali di letteratura. Per usarla in una nuova esecuzione, passa `--config .local/particle-research/research.toml` prima del sottocomando.

~~~sh
.venv/bin/python -m dynamic_proof --state .local/particle-research control paused
.venv/bin/python -m dynamic_proof --state .local/particle-research control running
.venv/bin/python -m dynamic_proof --state .local/particle-research run --lab particle_theory --cycles 30
~~~

`control stopped` ferma il lavoro attivo. Dopo il riavvio, `control running` rende nuovamente eseguibile la coda. Per esplorare un nuovo dominio o aumentare il budget di un problema concluso con limite computazionale, aggiorna il JSON e usa `submit`. Il registro mantiene anche il tentativo precedente.
