# Projektant kształtu impulsu — wersja webowa

Strona statyczna. Nie ma serwera, nie ma bazy, nie ma kosztów. Wszystko liczy
się w przeglądarce osoby, która wejdzie na stronę.

## Co jest czym

| plik | rola |
|---|---|
| `index.html` | cały interfejs, wykresy, edytor splajnu, kalibracja diody, licznik GoatCounter |
| `core.py` | **kopia oryginału, bez zmian.** Matematyka i kolejność operacji nietknięte |
| `builders.py` | buduje obwiednię `x` i mnożnik `new_filter_multiplier` z konfiguracji interfejsu |
| `app.py` | most między JavaScriptem a `core.py`; uruchamia `core.run()` i oddaje tablice |

## Dwie warstwy dokładności

To najważniejsza rzecz do zrozumienia przy tej aplikacji.

**Podgląd** — wszystko, co widać podczas przeciągania węzłów, liczy JavaScript
na siatce 4096 punktów. Musi nadążać za myszą, więc jest zgrubny. Panele
oznaczone plakietką „podgląd" pokazują właśnie to.

**Wynik** — po naciśnięciu `Zastosuj` strona pobiera Pythona i uruchamia
`core.py` na pełnej siatce 261 569 punktów, z prawdziwym
`scipy.signal.savgol_filter`. Stąd pochodzi obwiednia odtworzona, kroki
odwracania i plik CSV. Plakietka zmienia się na „dokładne N = 261 569".

Nic, co wychodzi z aplikacji jako plik, nie pochodzi z przybliżenia.

## Publikacja na GitHub Pages

1. Załóż konto na [github.com](https://github.com).
2. `New repository`, nazwa dowolna, widoczność **Public**, `Create`.
3. Przeciągnij na stronę repozytorium wszystkie cztery pliki z tego folderu.
4. `Settings` → `Pages` → `Source: Deploy from a branch` → gałąź `main`,
   katalog `/ (root)` → `Save`.
5. Po dwóch–trzech minutach strona działa pod adresem
   `https://TWOJANAZWA.github.io/NAZWA-REPO/`.

Aktualizacja: podmieniasz plik w repozytorium, adres zostaje ten sam.
Historia zmian jest zapisywana, więc zawsze można cofnąć.

## Test lokalny

`index.html` otwarty podwójnym kliknięciem **nie uruchomi Pythona** —
przeglądarka blokuje wtedy wczytywanie `core.py` (zasada `file://`). Interfejs
i podgląd zadziałają, `Zastosuj` nie. Do pełnego testu uruchom lokalny serwer:

```bash
python -m http.server 8000
```

i wejdź na `http://localhost:8000`.

## Liczniki

Licznik GoatCounter jest wpięty w `index.html` tuż nad `</head>`. Poza
odsłonami zliczane są zdarzenia całej ścieżki:

| zdarzenie | kiedy |
|---|---|
| `wejscie` | otwarcie strony |
| `splajn-edytowany` | pierwsza zmiana węzła — przeciągnięcie, dodanie, usunięcie lub wpisanie |
| `rownanie-dopasowane` | użycie `Dopasuj węzły` w edytorze równań |
| `obwiednia-zmieniona` | zmiana generatora obwiedni wejściowej |
| `trojkat-pobrany` | pobranie przebiegu trójkątnego do kalibracji |
| `kalibracja-dopasowana` | udane dopasowanie funkcji odwrotnej diody |
| `python-zadany` | pierwsze naciśnięcie `Zastosuj` — start pobierania Pythona |
| `python-gotowy` | Python i biblioteki załadowane |
| `obliczenie-dokladne` | `core.run()` zakończone powodzeniem |
| `csv-pobrany` | pobranie pliku CSV |
| `cala-procedura` | w jednej sesji: edycja splajnu **i** obliczenie **i** pobranie CSV |

Ostatnie zdarzenie jest tym, na które warto patrzeć — mówi, ilu ludzi przeszło
całą drogę, a nie tylko obejrzało wykresy. Każde zdarzenie liczy się raz na
sesję, więc powtórne kliknięcia nie zawyżają statystyk.

GoatCounter nie używa ciasteczek, więc strona nie potrzebuje okienka zgody.

## Ingerencje w środowisko

`core.py` jest nietknięty. Żeby mógł działać w przeglądarce, `app.py` robi dwie
rzeczy z otoczeniem — obie opisane w komentarzu w tym pliku:

* `pandas` jest podmieniany na pusty moduł. `core.py` go importuje, ale nigdzie
  nie używa, a pobranie prawdziwego pakietu kosztowałoby kilkanaście megabajtów.
* `plt.tight_layout` jest na czas przebiegu zamieniany na pustą funkcję.
  Wymusza ono pełne renderowanie rysunku 2×5 z krzywymi po 261 569 punktów, co
  w przeglądarce trwa kilkadziesiąt sekund. Rysunku i tak nie pokazujemy —
  wykresy rysuje interfejs z tablic liczbowych. Żadna liczba się nie zmienia.

## Pierwsze wejście

Pyodide z numpy, scipy i matplotlib to około 25 MB. Pobiera się dopiero po
naciśnięciu `Zastosuj`, z paskiem postępu, i zostaje w pamięci przeglądarki —
kolejne uruchomienia są natychmiastowe. Sam interfejs otwiera się od razu, więc
kto tylko ogląda, nie czeka ani sekundy.

Jeśli Pyodide kiedyś przestanie się ładować, w `index.html` na górze skryptu
jest stała `PYODIDE_VERSION` — wystarczy wpisać aktualną wersję z
[github.com/pyodide/pyodide/releases](https://github.com/pyodide/pyodide/releases).
