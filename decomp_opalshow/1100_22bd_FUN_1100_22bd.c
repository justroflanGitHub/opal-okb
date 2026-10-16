
void __cdecl16near FUN_1100_22bd(void)

{
  undefined1 uVar1;
  undefined1 *puVar2;
  byte bVar3;
  byte bVar4;
  int in_BX;
  undefined1 *puVar5;
  undefined2 uVar6;
  undefined2 unaff_DS;
  
  *(undefined1 *)0x102b = 1;
  puVar2 = (undefined1 *)*(undefined4 *)0x1120;
  uVar6 = (undefined2)((ulong)puVar2 >> 0x10);
  puVar5 = (undefined1 *)puVar2;
  uVar1 = *(undefined1 *)0x111f;
  if (*(char *)0x1125 == '\0') {
    for (; in_BX != 0; in_BX = in_BX + -1) {
      puVar2 = puVar5;
      puVar5 = puVar5 + 1;
      *puVar2 = uVar1;
    }
  }
  else {
    bVar4 = (byte)puVar2 & 7;
    bVar3 = 1U >> bVar4 | '\x01' << 8 - bVar4;
    bVar4 = *(byte *)(*(byte *)0x10e2 + 0x1013);
    do {
      while (bVar3 = bVar3 >> 1 | bVar3 << 7, (bVar4 & bVar3) == 0) {
        puVar5 = puVar5 + 1;
        in_BX = in_BX + -1;
        if (in_BX == 0) {
          return;
        }
      }
      puVar2 = puVar5;
      puVar5 = puVar5 + 1;
      *puVar2 = uVar1;
      in_BX = in_BX + -1;
    } while (in_BX != 0);
  }
  return;
}

