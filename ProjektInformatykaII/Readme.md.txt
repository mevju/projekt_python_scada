Projekt: Symulacja układu podgrzewania i chłodzenia (SCADA)
Autor: Mateusz Smyk
============================================================

1. OPIS PROJEKTU
Program jest graficzną symulacją układu podgrzewania i chłodzenia
wody, wykonaną w Pythonie z użyciem biblioteki PyQt5 oraz
pyqtgraph.

Aplikacja działa w stylu systemu SCADA i przedstawia:
- zbiorniki z wodą i węglem,
- rurociągi z animacją przepływu,
- proces grzania i chłodzenia,
- regulator temperatury z histerezą,
- wykres temperatury w czasie,
- panel sterowania dla użytkownika.

2. STRUKTURA PROGRAMU


Program składa się z trzech głównych klas:

1) class Zbiornik
   - reprezentuje zbiornik z wodą lub paliwem
   - przechowuje objętość, temperaturę i nazwę
   - rysuje poziom wody w zbiorniku
   - umożliwia ograniczenie maksymalnego napełnienia
     (np. Zbiornik 3 do 75% wysokości)

2) class Rura
   - reprezentuje rurociąg pomiędzy zbiornikami
   - posiada animację przepływu (linia przerywana)
   - kierunek przepływu zależny od parametru "direction"

3) class SCADA
   - główne okno aplikacji
   - zawiera całą logikę sterowania
   - obsługuje rysowanie, animacje i wykres
   - reaguje na działania użytkownika

3. OPIS ZBIORNIKÓW

Zbiorniki w systemie:

Zbiornik 1 (Z1)
- zbiornik wody zasilającej
- uzupełniany z rurociągu głównego

Zbiornik 2 (Z2 – Bufor)
- bufor ciepła
- utrzymywany w okolicach 70°C
- ogrzewany przez spalanie węgla lub grzałkę

Zbiornik 3 (Z3)
- główny zbiornik odbiorczy
- regulowana temperatura
- maksymalne wizualne napełnienie: 75%

Zbiornik 4 (Z4 – Chłodnia)
- dostarcza zimną wodę do chłodzenia Z3

Zbiornik 5 (Z5 – Węgiel)
- magazyn paliwa
- sterowany suwakiem i przyciskiem uzupełniania

4. ZASADA DZIAŁANIA

Program działa w pętli czasowej

1) Po naciśnięciu START:
   - uruchamiana jest automatyka
   - blokowana jest zmiana ilości węgla

2) Regulacja temperatury Z3:
   - odbywa się z użyciem histerezy
   - grzanie: T <= tzad - hi
   - chłodzenie: T >= tzad + hi

3) Grzanie:
   - woda z bufora (Z2) ogrzewa Z3
   - paliwem jest węgiel lub grzałka

4) Chłodzenie:
   - zimna woda z chłodni (Z4)
   - uruchamiana jest dmuchawa
   - wizualizacja silniejszego podmuchu

5) Po naciśnięciu STOP:
   - proces zostaje zatrzymany
   - Z3 stygnie naturalnie do temperatury otoczenia
   - wykres temperatury nadal się aktualizuje


5. PANEL STEROWANIA (UŻYTKOWNIK)

Użytkownik może sterować systemem za pomocą:

- Przycisk START
  Uruchamia automatykę procesu

- Przycisk STOP
  Zatrzymuje proces grzania i chłodzenia

- Suwak temperatury Zbiornika 3
  Zakres: 30–70 °C
  Ustawia temperaturę zadaną regulatora

- Suwak ilości węgla
  Zakres: 0–100 %
  Określa ilość paliwa na początku procesu

- Przycisk „Uzupełnij węgiel”
  Natychmiast napełnia zbiornik paliwa

6. WYKRES TEMPERATURY

- Wykres przedstawia temperaturę Zbiornika 3
- Oś X: czas
- Oś Y: temperatura
- Wykres aktualizuje się:
  - podczas pracy
  - po naciśnięciu STOP
  - podczas naturalnego stygnięcia

8. ELEMENTY WIZUALNE

- animowane rurociągi (tylko gdy płynie woda)
- dmuchawa z różną prędkością obrotów
- podział na instalację wewnętrzną i zewnętrzną


9. URUCHOMIENIE PROGRAMU

Program uruchamia się poleceniem:

python main.py

Po uruchomieniu wyświetla się okno aplikacji SCADA.

