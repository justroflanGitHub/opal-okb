
/* WARNING: Unable to track spacebase fully for stack */

undefined2 FUN_144d_148e(undefined2 param_1,uint param_2,char *param_3,int param_4)

{
  char *pcVar1;
  code *pcVar2;
  char cVar3;
  undefined2 uVar4;
  uint uVar5;
  char *pcVar6;
  char *pcVar7;
  int iVar8;
  char *pcVar9;
  undefined2 uVar10;
  undefined2 unaff_SS;
  undefined2 unaff_DS;
  bool bVar11;
  undefined2 uStack_12;
  undefined2 uStack_10;
  
  uVar4 = 0x144d;
  if (*(uint *)0x3ba <= param_2) {
LAB_144d_14a1:
    uVar4 = FUN_144d_0ac1();
    return uVar4;
  }
  if (*(int *)0x5c0 == -0x292a) {
    uVar4 = 0x1000;
    (*(code *)*(undefined2 *)0x5c2)();
  }
  if ((*(byte *)(param_2 + 0x3bc) & 0x20) != 0) {
    bVar11 = false;
    pcVar2 = (code *)swi(0x21);
    (*pcVar2)();
    if (bVar11) goto LAB_144d_14a1;
  }
  if ((*(byte *)(param_2 + 0x3bc) & 0x80) != 0) {
    pcVar6 = (char *)param_3;
    bVar11 = true;
    iVar8 = param_4;
    pcVar9 = pcVar6;
    if (param_4 == 0) {
      uVar4 = FUN_144d_159c();
      return uVar4;
    }
    do {
      if (iVar8 == 0) break;
      pcVar1 = pcVar9;
      pcVar9 = pcVar9 + 1;
      bVar11 = *pcVar1 == '\n';
      iVar8 = iVar8 + -1;
    } while (!bVar11);
    if (bVar11) {
      pcVar7 = pcVar6;
      uStack_12 = uVar4;
      uStack_10 = param_3._2_2_;
      uVar5 = FUN_144d_17d8();
      uVar4 = uStack_10;
      if (0xa8 < uVar5) {
        pcVar9 = (char *)&uStack_10;
        iVar8 = 0x200;
        if (uVar5 < 0x228) {
          iVar8 = 0x80;
        }
        iVar8 = -iVar8;
        pcVar7 = (char *)((int)&uStack_10 + iVar8);
        *(undefined2 *)((int)&uStack_12 + iVar8) = unaff_SS;
        uVar10 = *(undefined2 *)((int)&uStack_12 + iVar8);
        do {
          pcVar1 = pcVar6;
          pcVar6 = pcVar6 + 1;
          cVar3 = *pcVar1;
          if (cVar3 == '\n') {
            cVar3 = '\r';
            if (pcVar7 == pcVar9) {
              *(undefined2 *)((int)&uStack_12 + iVar8) = 0x5a03;
              cVar3 = FUN_144d_1551();
            }
            pcVar1 = pcVar7;
            pcVar7 = pcVar7 + 1;
            *pcVar1 = cVar3;
            cVar3 = '\n';
          }
          if (pcVar7 == pcVar9) {
            *(undefined2 *)((int)&uStack_12 + iVar8) = 0x5a0e;
            cVar3 = FUN_144d_1551();
          }
          pcVar1 = pcVar7;
          pcVar7 = pcVar7 + 1;
          *pcVar1 = cVar3;
          param_4 = param_4 + -1;
        } while (param_4 != 0);
        *(undefined2 *)((int)&uStack_12 + iVar8) = 0x59f8;
        FUN_144d_1551();
        uVar4 = FUN_144d_159c();
        return uVar4;
      }
      uStack_12 = 0x144d;
      uStack_12 = FUN_144d_1770();
      bVar11 = pcVar9 < pcVar7;
      if (pcVar9 != pcVar7) {
        pcVar2 = (code *)swi(0x21);
        iVar8 = (*pcVar2)();
        if ((bVar11) || (iVar8 == 0)) {
          uVar4 = FUN_144d_0ac1();
          return uVar4;
        }
      }
      return uStack_12;
    }
  }
  uVar4 = FUN_144d_15ad();
  return uVar4;
}

