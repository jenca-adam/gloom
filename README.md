# GLOOM - Záverečný projekt z informatiky

## Úvod

Hra GLOOM je inšpirovaná hrami ako DOOM a Half-Life, ibaže ide o dvojrozmerné prevedenie klasického konceptu strieľačky.
Hráč sa pohybuje cez miestnosti a strieľa do nepriateľov. Počas hry môže zbierať zbrane padlých nepriateľov.
Level sa skončí až vtedy, keď hráč zabije všetkých nepriateľov v leveli. Potom môže postúpiť ďalej.

## Základy

### Ovládanie
Hráč sa hýbe klávesami W,A,S,D a strieľa kliknutím myši.
Náboj sa po vystrelení hýbe smerom ku kurzoru myši.

### Zbrane
Zbrane majú nasledovné atribúty:

- `rng` - ako ďaleko náboj z tejto zbrane zaletí(v pixeloch)
- `dmg` - silu poškodenia - celková sila náboja 
- `pierce` - popisuje pomer poškodenia tela a brnenia(v %)
- `speed` - rýchlosť náboja 
- `spread` - uhol v ktorom sú jednotlivé náboje rozložené
- `bullets_per_mg` - počet nábojov v jednom zásobníku
- `bullets_per_shot` - počet nábojov v jednom výstrele
- `bullet_size` - veľkosť náboja
- `rate` - rýchlosť streľby, v tickoch
- `reload_rate` - rýchlosť nabitia zbrane, v tickoch


#### Pištoľ(Pistol)
- `rng = 500`
- `dmg = 10`
- `pierce=50`
- `speed=10`
- `spread=0`
- `bullets_per_mg=15`
- `bullets_per_shot=1`
- `bullet_size = 3`
- `rate=50`
- `reload_rate=200`

### Levely
Level pozostáva zo:

- štvorcových stien
- nepriateľov
- itemov

Levely sú uložené v textových súboroch pre ľahšie navrhovanie levelov.
Steny sú označované ako `#`, nepriatelia veľkými písmenami a itemy malými písmenami.

## Technické detaily
