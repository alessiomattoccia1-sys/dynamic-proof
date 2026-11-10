# Metodo scientifico

Il settore contiene solo fermioni di Weyl sinistrorsi e singoletti degli altri gruppi di gauge. In quattro dimensioni, le condizioni di anomalia perturbativa locale nel settore sono \(\sum_i q_i=0\) e \(\sum_i q_i^3=0\). Una carica opposta permette un bilineare invariante. La chiralità stretta richiede che il multinsieme non contenga una coppia opposta e che tutte le cariche siano non nulle. La normalizzazione primitiva usa il MCD dei valori assoluti. [Costa, Dobrescu e Fox 2019](https://doi.org/10.1103/PhysRevLett.123.151601)

## Classificazione intera

Ogni multinsieme ha un unico vettore non decrescente. Per \(n\) fermioni e limite \(B\), l'enumerazione diretta contiene \(\binom{2B+n-1}{n}\) elementi. Nella strategia ridotta, da ogni prefisso ordinato di lunghezza \(n-2\) si ottengono \(s=x+y\) e \(t=x^3+y^3\). Per \(s\ne0\), si deve avere \(xy=(s^3-t)/(3s)\). Divisibilità, discriminante quadrato, parità, ordinamento e limiti forniscono il test esatto sulle radici. Per \(s=0\) serve \(t=0\) e \(y=-x\), escluso nella chiralità stretta. La completezza si riferisce alle unità previste dalla strategia.

Il modello SMT usa molteplicità intere \(m_q\ge0\), con somme lineari dei coefficienti \(1,q,q^3\). Si vieta il supporto simultaneo di \(m_q,m_{-q}\). Per ogni primo \(p\le B\) la primitività richiede una carica presente non divisibile per \(p\). Bloccare ciascun modello e ottenere UNSAT sul residuo chiude il confronto con l'enumerazione. In caso di limite SMT, il completamento lineare indipendente usa un prefisso lungo \(n-1\) quando il suo costo rientra nel budget. Il rapporto conserva anche l'esito terminale Z3.

## Matrice di massa

I soli termini ammessi sono \(y_{ij,a}\phi_a\psi_i\psi_j\) o il termine con \(\phi_a^\dagger\), con \(|q_i+q_j|=|h_a|\). Con VEV non nulli e coefficienti indipendenti per entrata simmetrica ammessa, il rango generico è il massimo rango realizzabile sul supporto.

Un abbinamento massimo fra righe e colonne del supporto ha la stessa cardinalità di una copertura minima. La copertura, verificata direttamente su tutte le entrate ammesse, limita il rango superiore. Gli archi dell'abbinamento sullo stesso insieme di indici formano cammini, cappi e cicli. Coppie adiacenti su ogni cammino o ciclo pari danno blocchi invertibili di ordine 2. I cappi danno blocchi di ordine 1. Un ciclo dispari semplice con le entrate ammesse poste a 1 ha determinante 2. Questi blocchi danno un testimone razionale che raggiunge il limite superiore. Il codice controlla l'uguaglianza con eliminazione su \(\mathbb Q\) e SymPy. Il determinante simbolico è espanso fino a ordine 6 e per i supporti sufficientemente sparsi fino a ordine 8. La copertura certifica gli zeri identici.

La ricerca prova gli insiemi di scalari per cardinalità crescente. Ogni carica scalare che non appare fra le somme assolute di coppia dà un supporto vuoto. La prima matrice invertibile certifica il minimo. Per una conclusione negativa nel dominio richiesto devono essere esauriti tutti gli insiemi previsti.

## Ostruzione di parità

Un termine non nullo del determinante richiederebbe \(n\) somme \(q_{\sigma(i)}+q_i\) con totale \(2\sum_i q_i=0\). Se tutte le somme ammesse sono multipli dispari di un intero \(d\ne0\), dividere per \(d\) produce una somma dispari quando \(n\) è dispari. Ogni termine del determinante ha quindi un fattore zero. Per uno scalare si pone \(d=h\). Per più scalari con uguale valutazione 2-adica si può scegliere \(d\) uguale alla potenza comune di 2. Il sorgente Lean verifica il determinante su matrici sopra un anello commutativo. Le due dichiarazioni controllate sono `dp_particle_one_scalar` e `dp_particle_odd_det`.

## Due cariche scalari

Per \(0<a<b\) interi, poniamo \(g=\gcd(a,b)\), \(a'=a/g\), \(b'=b/g\). Una somma di \(n\) etichette da \(\{\pm a,\pm b\}\) vale zero se le differenze dei conteggi \(u,v\) soddisfano \(a'u+b'v=0\). Per coprimalità, \((u,v)=(b'k,-a'k)\). Il numero minimo di termini compatibile con \(k\) è \(|k|(a'+b')\) e ogni termine aggiuntivo entra in una coppia opposta. Per \(n\) dispari la condizione aritmetica è quindi \(a'+b'\) dispari e \(a'+b'\le n\). Viceversa, \(k=1\) e l'aggiunta di coppie producono una somma di lunghezza \(n\).

Per cinque fermioni i rapporti primitivi aritmeticamente possibili sono \(1:2\), \(1:4\) e \(2:3\). La realizzabilità delle singole entrate dipende dalle cariche fermioniche fissate. PT-006 cerca un supporto singolare pur in presenza di una somma scalare compatibile. PT-007 ricontrolla il criterio con programmazione dinamica sulle somme finite e conserva l'obbligo di formalizzare l'equivalenza aritmetica in Lean.

## Un solo scalare e divisibilità per quattro

Sia \(h>0\) intero e sia \(M\) supportata sulle coppie con \(q_i+q_j=\pm h\). Se \(\sum_i q_i=0\) e almeno uno fra \(h/2,-h/2\) è assente dal multinsieme delle cariche, allora \(\det M\ne0\) implica \(4\mid n\).

Un termine non nullo del determinante fornisce una permutazione in cui le etichette \(+h,-h\) compaiono \(n/2\) volte ciascuna, poiché la loro somma è \(2\sum_i q_i=0\). Sul grafo dei valori distinti delle cariche ogni vertice ha al più un vicino per ciascuna etichetta. Un ciclo semplice senza cappi dovrebbe alternare le etichette. Due riflessioni diverse \(x\mapsto h-x\) e \(x\mapsto -h-x\) compongono una traslazione non nulla e un numero pari di passi alternati non chiude il ciclo. Il grafo senza cappi è quindi una foresta. Nei cicli della permutazione ogni arco non cappio è attraversato un numero pari di volte, perché separa un taglio della foresta. Il segno il cui punto fisso è assente non ha cappi. Il suo conteggio \(n/2\) è pari.

Una seconda dimostrazione usa le molteplicità. Siano \(p(x),m(x)\) i conteggi delle etichette positiva e negativa che partono da carica \(x\) nella permutazione. Il bilancio dei conteggi dà

\[
p(x)+m(x)=p(h-x)+m(-h-x).
\]

La differenza \(D(x)=p(x)-p(h-x)=m(-h-x)-m(x)\) è antisimmetrica sotto entrambe le riflessioni, dunque ha periodo \(2h\). Ha supporto finito, quindi è identicamente nulla. Ciascun conteggio è così invariante per la propria riflessione. Il segno privo del punto fisso ha conteggio pari, per cui \(4\mid n\).

La chiralità stretta assicura l'ipotesi di assenza di almeno un punto fisso. Il limite noto \(n\ge5\) con entrambe le anomalie implica allora \(n\ge8\) per un solo scalare. PT-012 raggiunge il limite con \(q=(-7,-6,-3,1,1,2,4,8)\) e \(h=5\). Le quattro coppie hanno somme \(+5,+5,-5,-5\) e differenze assolute \(3,11,7,9\). La somma dei cubi di una coppia di somma \(s\) e differenza \(d\) è \((s^3+3sd^2)/4\). L'identità \(3^2+11^2=7^2+9^2=130\) dà la cancellazione cubica. Quattro blocchi simmetrici fuori diagonale con coefficiente 1 danno determinante 1. Se sono presenti entrambi i punti fissi, \(q=(-1,1)\), \(h=2\) consente una matrice diagonale invertibile a \(n=2\).
