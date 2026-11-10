# Risultati del primo programma Particle Theory

Mac mini, 10–11 novembre 2026. Il Runner ha concluso 20 tentativi, inclusi i checkpoint, su un budget di 30. PT-001–PT-010 sono partiti dalla coda iniziale. Il risultato di PT-010 ha motivato PT-011 e PT-012, sottoposti nello stesso registro. L'esecuzione successiva ha trovato la coda esaurita.

| Problema | Esito verificato |
| --- | --- |
| PT-001 | 26.334 multinsiemi. Due assegnazioni orientate, una classe primitiva per segno globale. L'enumerazione e Z3 coincidono. |
| PT-002 | Tutti i dieci supporti a uno scalare sono singolari per il modello di riferimento. Il minimo è due. Con \(h=(1,2)\) si ottiene rango 5, determinante \(b^2c^2d\) e un testimone di determinante 1. |
| PT-003 | Lean verifica il caso dispari a uno scalare e la versione dei multipli dispari di un intero comune. La ricerca finita ha esaminato 1.365 prefissi e 1.174 supporti a uno scalare. |
| PT-004 | Sei classi primitive chirali con \(n=6\), \(|q_i|\le12\), su 17.550 prefissi ordinati. |
| PT-005 | Due classi prive di anomalie locali con \(n=5\), \(|q_i|\le14\). Una ammette rango 5 nel pool di scalari 1–6 e con al più due scalari. È la classe del pilot, con coppie \((1,2)\) e \((2,3)\). |
| PT-006 | Il modello del pilot con \(h=(3,6)\) ha la somma di etichette \(6+3+3-6-6=0\), ma il rango generico è 4. Il controesempio confuta la sufficienza aritmetica nel registro. |
| PT-007 | Per \(n\) dispari il criterio aritmetico a due scalari è \((a+b)/\gcd(a,b)\) dispari e al più \(n\). Derivazione e 330 confronti esatti con programmazione dinamica. |
| PT-008 | UNSAT nel dominio a quattro fermioni, \(|q_i|\le9\), dopo 5.985 multinsiemi e verifica Z3. |
| PT-009 | 22 classi primitive chirali con \(n=7\), \(|q_i|\le12\), su 98.280 prefissi ordinati. |
| PT-010 | Nessuna delle sei classi di PT-004 raggiunge rango 6 con un solo scalare. Il massimo rango di ciascuna è 4 nel dominio esaminato. |
| PT-011 | Due dimostrazioni analitiche di \(4\mid n\) quando un solo scalare dà massa piena, \(\sum q_i=0\) e almeno uno dei punti fissi \(h/2,-h/2\) è assente. Il controllo finito ha esaminato 2.002 prefissi e 1.056 supporti a sei fermioni. |
| PT-012 | \(q=(-7,-6,-3,1,1,2,4,8)\), \(h=5\). Entrambe le somme di anomalia sono zero. Il supporto ammette rango 8 e un testimone intero di determinante 1. |

## Soglia a otto fermioni

Il teorema PT-011 dà un limite inferiore di otto nel settore chirale con le due anomalie cancellate, usando il minimo generale di cinque fermioni della letteratura. La costruzione PT-012 raggiunge il limite con un solo scalare. Il fascicolo riporta la dimostrazione tramite il grafo delle cariche, quella tramite le molteplicità e il caso \(n=2\) che mostra il ruolo dell'ipotesi sui punti fissi. La formalizzazione Lean di PT-011 e la verifica di priorità bibliografica sono aperte. [Metodo e dimostrazioni](SCIENTIFIC_METHOD.md) · [Costa, Dobrescu e Fox 2020](https://doi.org/10.1103/PhysRevD.101.095032)

Il registro ha classificato PT-011 e PT-012 come nuovi per la sessione. Per PT-011 sono disponibili le risposte di Crossref, arXiv e INSPIRE-HEP e il confronto con le fonti primarie. La ricerca mirata sulla soglia con masse Majorana ammesse resta aperta. [Confronto bibliografico](PRIOR_ART.md)

I fascicoli locali sono in `.local/particle-research/reports/`. I tentativi 5, 11 e 19 contengono le bozze LaTeX. Il tentativo 20 contiene matrice, polinomio simbolico e testimone del modello a otto fermioni. [Istruzioni per riprodurre e riprendere](REPRODUCIBILITY.md)
