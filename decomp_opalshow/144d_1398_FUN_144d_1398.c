
/* WARNING: Removing unreachable block (ram,0x0001595c) */
/* WARNING: Removing unreachable block (ram,0x00015951) */

void FUN_144d_1398(undefined2 param_1,uint param_2,undefined4 param_3,int param_4)

{
  char *pcVar1;
  char cVar2;
  code *pcVar3;
  undefined2 uVar4;
  undefined1 extraout_AH;
  undefined1 extraout_AH_00;
  int iVar5;
  undefined1 extraout_AH_01;
  int iVar7;
  uint extraout_DX;
  char *pcVar8;
  char *pcVar9;
  undefined2 unaff_DS;
  undefined1 uVar10;
  bool bVar11;
  undefined4 uVar12;
  char cVar6;
  
  if (((*(uint *)0x3ba <= param_2) || (param_4 == 0)) || ((*(byte *)(param_2 + 0x3bc) & 2) != 0)) {
LAB_144d_1420:
    FUN_144d_0ac1();
    return;
  }
  uVar10 = *(uint *)0x5c0 < 0xd6d6;
  if (*(uint *)0x5c0 == 0xd6d6) {
    (*(code *)*(undefined2 *)0x5c2)();
  }
  pcVar3 = (code *)swi(0x21);
  uVar12 = (*pcVar3)();
  pcVar9 = (char *)((ulong)uVar12 >> 0x10);
  if (((bool)uVar10) || ((*(byte *)(param_2 + 0x3bc) & 0x80) == 0)) goto LAB_144d_1420;
  *(byte *)(param_2 + 0x3bc) = *(byte *)(param_2 + 0x3bc) & 0xfb;
  if ((int)uVar12 == 0) goto LAB_144d_1420;
  uVar4 = 0xd00;
  if (*pcVar9 == '\n') {
    *(byte *)(param_2 + 0x3bc) = *(byte *)(param_2 + 0x3bc) | 4;
  }
LAB_144d_1402:
  pcVar8 = (char *)((ulong)uVar12 >> 0x10);
  iVar7 = (int)uVar12;
  pcVar1 = pcVar8 + 1;
  cVar2 = *pcVar8;
  cVar6 = (char)((uint)uVar4 >> 8);
  uVar4 = CONCAT11(cVar6,cVar2);
  if (cVar2 == cVar6) {
    if (iVar7 != 1) {
      if (*pcVar1 != '\n') goto LAB_144d_1413;
      goto LAB_144d_1416;
    }
    bVar11 = false;
    if ((*(byte *)(param_2 + 0x3bc) & 0x40) == 0) {
      pcVar3 = (code *)swi(0x21);
      iVar5 = (*pcVar3)();
      if (!bVar11) {
        uVar10 = 0;
        if (iVar5 != 0) {
          pcVar3 = (code *)swi(0x21);
          (*pcVar3)();
          iVar7 = 1;
          uVar10 = extraout_AH_01;
        }
        uVar4 = CONCAT11(uVar10,0xd);
        goto LAB_144d_1413;
      }
      goto LAB_144d_1420;
    }
    pcVar3 = (code *)swi(0x21);
    (*pcVar3)();
    bVar11 = false;
    uVar10 = extraout_AH;
    if ((extraout_DX & 0x20) == 0) {
      pcVar3 = (code *)swi(0x21);
      (*pcVar3)();
      uVar10 = extraout_AH_00;
      if (bVar11) goto LAB_144d_1420;
    }
    uVar4 = CONCAT11(uVar10,10);
  }
  else if (cVar2 == '\x1a') {
    *(byte *)(param_2 + 0x3bc) = *(byte *)(param_2 + 0x3bc) | 2;
    goto LAB_144d_1420;
  }
LAB_144d_1413:
  *pcVar9 = (char)uVar4;
  pcVar9 = pcVar9 + 1;
LAB_144d_1416:
  uVar12 = CONCAT22(pcVar1,iVar7 + -1);
  if (iVar7 + -1 == 0) goto LAB_144d_1420;
  goto LAB_144d_1402;
}

