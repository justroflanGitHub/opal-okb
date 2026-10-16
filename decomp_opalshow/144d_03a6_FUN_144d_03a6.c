
void FUN_144d_03a6(void)

{
  char *pcVar1;
  char *pcVar2;
  code *pcVar3;
  char cVar4;
  int iVar5;
  char extraout_DH;
  uint extraout_DX;
  undefined2 in_BX;
  int iVar6;
  int unaff_SI;
  char *pcVar7;
  int unaff_DI;
  char *pcVar8;
  undefined2 unaff_ES;
  undefined2 unaff_SS;
  undefined2 unaff_DS;
  bool bVar9;
  undefined2 uStack_4;
  
  FUN_144d_054a();
  FUN_144d_05bf();
  if (*(int *)0x5c0 == -0x292a) {
    uStack_4 = 0x4894;
    (*(code *)*(undefined2 *)0x5c4)();
  }
  uStack_4 = 0xff;
  (*(code *)*(undefined2 *)0x340)();
  *(char *)(unaff_SI + -0x32d0) = *(char *)(unaff_SI + -0x32d0) + extraout_DH;
  *(uint *)(&stack0x03b3 + unaff_DI) = *(uint *)(&stack0x03b3 + unaff_DI) & (uint)&uStack_4;
  pcVar3 = (code *)swi(0x21);
  (*pcVar3)();
  *(undefined2 *)0x3a1 = in_BX;
  *(undefined2 *)0x3a3 = unaff_ES;
  pcVar3 = (code *)swi(0x21);
  (*pcVar3)();
  if (*(int *)0x5d0 != 0) {
    bVar9 = false;
    (*(code *)*(undefined2 *)0x5ce)();
    if (bVar9) {
      FUN_144d_0544();
      return;
    }
    (*(code *)*(undefined2 *)0x5ce)();
  }
  iVar6 = *(int *)0x2c;
  if (iVar6 != 0) {
    pcVar8 = (char *)0x0;
    do {
      if (*pcVar8 == '\0') break;
      iVar5 = 0xc;
      pcVar7 = (char *)0x394;
      bVar9 = false;
      do {
        if (iVar5 == 0) break;
        iVar5 = iVar5 + -1;
        pcVar2 = pcVar8;
        pcVar8 = pcVar8 + 1;
        pcVar1 = pcVar7;
        pcVar7 = pcVar7 + 1;
        bVar9 = *pcVar1 == *pcVar2;
      } while (bVar9);
      if (bVar9) {
        pcVar7 = (char *)0x3bc;
        iVar5 = (int)*pcVar8;
        do {
          pcVar8 = pcVar8 + 1;
          cVar4 = '\0';
          if (*pcVar8 != -1) {
            cVar4 = *pcVar8;
          }
          pcVar1 = pcVar7;
          pcVar7 = pcVar7 + 1;
          *pcVar1 = cVar4;
          iVar5 = iVar5 + -1;
        } while (iVar5 != 0);
        break;
      }
      iVar5 = 0x7fff;
      bVar9 = true;
      do {
        if (iVar5 == 0) break;
        iVar5 = iVar5 + -1;
        pcVar1 = pcVar8;
        pcVar8 = pcVar8 + 1;
        bVar9 = *pcVar1 == '\0';
      } while (!bVar9);
    } while (bVar9);
  }
  iVar6 = 4;
  do {
    bVar9 = false;
    *(byte *)(iVar6 + 0x3bc) = *(byte *)(iVar6 + 0x3bc) & 0xbf;
    pcVar3 = (code *)swi(0x21);
    (*pcVar3)();
    if ((!bVar9) && ((extraout_DX & 0x80) != 0)) {
      *(byte *)(iVar6 + 0x3bc) = *(byte *)(iVar6 + 0x3bc) | 0x40;
    }
    iVar6 = iVar6 + -1;
  } while (-1 < iVar6);
  FUN_144d_0530();
  FUN_144d_0530();
  return;
}

