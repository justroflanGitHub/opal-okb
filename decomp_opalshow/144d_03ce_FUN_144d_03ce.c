
void __cdecl16far FUN_144d_03ce(void)

{
  char *pcVar1;
  char *pcVar2;
  code *pcVar3;
  char cVar4;
  undefined2 uVar5;
  int iVar6;
  uint extraout_DX;
  undefined2 in_BX;
  int iVar7;
  char *pcVar8;
  char *pcVar9;
  undefined2 unaff_ES;
  undefined2 unaff_SS;
  undefined2 unaff_DS;
  bool bVar10;
  
  pcVar3 = (code *)swi(0x21);
  uVar5 = (*pcVar3)();
  *(undefined2 *)0x3b5 = uVar5;
  pcVar3 = (code *)swi(0x21);
  (*pcVar3)();
  *(undefined2 *)0x3a1 = in_BX;
  *(undefined2 *)0x3a3 = unaff_ES;
  pcVar3 = (code *)swi(0x21);
  (*pcVar3)();
  if (*(int *)0x5d0 != 0) {
    bVar10 = false;
    (*(code *)*(undefined2 *)0x5ce)();
    if (bVar10) {
      FUN_144d_0544();
      return;
    }
    (*(code *)*(undefined2 *)0x5ce)();
  }
  iVar7 = *(int *)0x2c;
  if (iVar7 != 0) {
    pcVar9 = (char *)0x0;
    do {
      if (*pcVar9 == '\0') break;
      iVar6 = 0xc;
      pcVar8 = (char *)0x394;
      bVar10 = false;
      do {
        if (iVar6 == 0) break;
        iVar6 = iVar6 + -1;
        pcVar2 = pcVar9;
        pcVar9 = pcVar9 + 1;
        pcVar1 = pcVar8;
        pcVar8 = pcVar8 + 1;
        bVar10 = *pcVar1 == *pcVar2;
      } while (bVar10);
      if (bVar10) {
        pcVar8 = (char *)0x3bc;
        iVar6 = (int)*pcVar9;
        do {
          pcVar9 = pcVar9 + 1;
          cVar4 = '\0';
          if (*pcVar9 != -1) {
            cVar4 = *pcVar9;
          }
          pcVar1 = pcVar8;
          pcVar8 = pcVar8 + 1;
          *pcVar1 = cVar4;
          iVar6 = iVar6 + -1;
        } while (iVar6 != 0);
        break;
      }
      iVar6 = 0x7fff;
      bVar10 = true;
      do {
        if (iVar6 == 0) break;
        iVar6 = iVar6 + -1;
        pcVar1 = pcVar9;
        pcVar9 = pcVar9 + 1;
        bVar10 = *pcVar1 == '\0';
      } while (!bVar10);
    } while (bVar10);
  }
  iVar7 = 4;
  do {
    bVar10 = false;
    *(byte *)(iVar7 + 0x3bc) = *(byte *)(iVar7 + 0x3bc) & 0xbf;
    pcVar3 = (code *)swi(0x21);
    (*pcVar3)();
    if ((!bVar10) && ((extraout_DX & 0x80) != 0)) {
      *(byte *)(iVar7 + 0x3bc) = *(byte *)(iVar7 + 0x3bc) | 0x40;
    }
    iVar7 = iVar7 + -1;
  } while (-1 < iVar7);
  FUN_144d_0530();
  FUN_144d_0530();
  return;
}

