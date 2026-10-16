
void __cdecl16near FUN_1100_3444(void)

{
  undefined1 *puVar1;
  int *piVar2;
  code *pcVar3;
  byte bVar4;
  undefined1 uVar6;
  int in_CX;
  byte in_BL;
  undefined1 *unaff_SI;
  int *unaff_DI;
  undefined2 unaff_ES;
  undefined2 unaff_SS;
  undefined2 unaff_DS;
  int iVar5;
  
  if (*(char *)0x2d6 != '\0') {
    do {
      pcVar3 = (code *)swi(0x10);
      (*pcVar3)();
      pcVar3 = (code *)swi(0x10);
      (*pcVar3)();
      in_CX = in_CX + -1;
    } while (in_CX != 0);
    return;
  }
  FUN_1100_349c();
  iVar5 = (uint)in_BL << 8;
  if ((*(char *)0x1112 == '\x02') && ((*(byte *)0x1111 & 1) != 0)) {
    while( true ) {
      uVar6 = (undefined1)((uint)iVar5 >> 8);
      bVar4 = in(0x3da);
      iVar5 = CONCAT11(uVar6,bVar4);
      if ((bVar4 & 8) != 0) break;
      if ((bVar4 & 1) == 0) {
        puVar1 = unaff_SI;
        unaff_SI = unaff_SI + 1;
        iVar5 = CONCAT11(uVar6,*puVar1);
        do {
          bVar4 = in(0x3da);
        } while ((bVar4 & 1) == 0);
        piVar2 = unaff_DI;
        unaff_DI = unaff_DI + 1;
        *piVar2 = iVar5;
        in_CX = in_CX + -1;
        if (in_CX == 0) {
          return;
        }
      }
    }
  }
  do {
    puVar1 = unaff_SI;
    unaff_SI = unaff_SI + 1;
    iVar5 = CONCAT11((char)((uint)iVar5 >> 8),*puVar1);
    piVar2 = unaff_DI;
    unaff_DI = unaff_DI + 1;
    *piVar2 = iVar5;
    in_CX = in_CX + -1;
  } while (in_CX != 0);
  return;
}

