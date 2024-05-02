# GLOOM - Záverečný projekt z informatiky

## Úvod

Hra GLOOM je inšpirovaná hrami ako DOOM a Half-Life, ibaže ide o dvojrozmerné prevedenie klasického konceptu strieľačky.
Hráč sa pohybuje cez miestnosti a strieľa do nepriateľov. Počas hry môže zbierať zbrane padlých nepriateľov.
Level sa skončí vtedy, keď hráč najde východ z levelu. 

## Základy

### Ovládanie
Hráč sa hýbe klávesami W,A,S,D a strieľa kliknutím myši.
Náboj sa po vystrelení hýbe smerom ku kurzoru myši.
Zbrane sa prepínajú klávesmi 1 až 8

### Zbrane
Existujú nasledovné zbrane:

- `Pistol`
- `Shotgun`
- `MachineGun`
- `RocketLauncher`
- `DoubleBarrelShotgun`
- `DesertEagle`
- `AssaultRifle`
- `QuadBarrelShotgun`

Každá zbraň má istý počet nábojov v zásobníku a istý počet nábojov mimo neho.
Stav zásobníka sa ukazuje v pravom dolnom rohu hracej plochy.

### Itemy
Existujú nasledovné itemy:

- `MediKit`
- `StimPack`
- `SpeedBooster`
- `WeaponPickup`(pre každú zbraň)
- `Armor`
- `Keycard` (red, yellow, blue)

Ďalšie itemy môžu byť pridané počas programovania hry.

#### MediKit
Vylieči hráča za 25 HP(hráč začína na 100)

#### StimPack
Vylieči hráča za 10 HP

#### SpeedBooster
Zrýchli hráča na 20 sekúnd

#### WeaponPickup
Pridá zbraň hráčovi do inventára.
Ak hráč už zbraň má, pridá mu jeden plný zásobník.

#### Armor
Nastaví brnenie hráča na 100.
Brnenie redukuje poškodenie od nepriateľov.

#### Keycard
Keycard vie otvoriť príslušné dvere(rovnakej farby)

### Dvere
Cez dvere sa nedá prejsť ak hráč nemá príslušný keycard.
Ak hráč narazí do dverí a má príslušný keycard, otvoria sa.

### Viditeľnosť
Steny, dvere, nepriatelia ani itemy nie sú viditeľné ak sú zakryté dverami alebo stenou.
Ak ich už hráč videl, zostávajú vykreslené na obrazovke, len v inej farbe


### Levely

Levely sú štvorcové siete pozostávajúce zo:

- štvorcových stien
- nepriateľov
- itemov
- dverí

Každý level má vchod a východ.
Levely sú uložené v textových súboroch pre ľahšie navrhovanie levelov.
Steny sú označované ako `#`, nepriatelia veľkými písmenami a itemy malými písmenami.

Súbor z levelmi nájdete na adrese https://github.com/jenca-adam/gloom/blob/main/default.gloom .


