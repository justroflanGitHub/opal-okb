
/* WARNING: Control flow encountered bad instruction data */
/* WARNING: Instruction at (ram,0x00023f2c) overlaps instruction at (ram,0x00023f2b)
    */

void __stdcall16far FUN_2000_3e4c(void)

{
  byte *pbVar1;
  char *pcVar2;
  int *piVar3;
  code *pcVar4;
  undefined1 in_AL;
  undefined1 uVar5;
  byte bVar6;
  byte *pbVar7;
  int iVar8;
  int iVar9;
  int iVar10;
  byte extraout_DL;
  byte extraout_DL_00;
  uint extraout_DX;
  undefined2 extraout_DX_00;
  undefined2 extraout_DX_01;
  undefined2 extraout_DX_02;
  undefined2 extraout_DX_03;
  byte *in_BX;
  int iVar11;
  int unaff_BP;
  byte *unaff_SI;
  undefined1 *puVar12;
  byte *unaff_DI;
  undefined2 unaff_ES;
  undefined2 uVar13;
  undefined2 unaff_SS;
  undefined2 unaff_DS;
  char cVar14;
  bool in_ZF;
  undefined1 uVar15;
  int in_stack_0000000e;
  
  out(0x39,in_AL);
  if (in_ZF) {
    if (*(int *)0x39e0 == 0 && *(int *)0x39e2 == 0) {
      return;
    }
    *(undefined2 *)0x53b6 = 5;
  }
  *(undefined2 *)0x538a = 0;
  *(undefined2 *)(unaff_BP + -2) = *(undefined2 *)0x53ac;
  *(undefined2 *)0x537e = *(undefined2 *)0x53b6;
  if (*(int *)(unaff_BP + -2) < *(int *)0x537e) {
    return;
  }
  pcVar4 = (code *)swi(0x35);
  uVar5 = (*pcVar4)();
  out(extraout_DX_01,uVar5);
  pcVar4 = (code *)swi(0x39);
  bVar6 = (*pcVar4)();
  cVar14 = bVar6 < *unaff_DI;
  pcVar4 = (code *)swi(0x39);
  iVar10 = (*pcVar4)();
  pbVar1 = unaff_DI + 1 + unaff_BP + -0x33;
  *pbVar1 = *pbVar1 + 0x3d + cVar14;
  if (iVar10 < 5) {
    pcVar4 = (code *)swi(0x35);
    uVar5 = (*pcVar4)();
    out(extraout_DX_02,uVar5);
    pcVar4 = (code *)swi(0x39);
    (*pcVar4)();
    pbVar7 = unaff_DI + 2;
    unaff_DI[1] = *unaff_SI;
    pcVar4 = (code *)swi(0x39);
    (*pcVar4)();
    uVar15 = (byte *)*(undefined2 *)0x53d8 == in_BX;
    pcVar4 = (code *)swi(0x35);
    uVar5 = (*pcVar4)();
    out(extraout_DX_03,uVar5);
    pcVar4 = (code *)swi(0x39);
    cVar14 = (*pcVar4)();
    if ((bool)uVar15) {
      out(0xb8,cVar14);
      in_BX[(int)(unaff_SI + 1)] =
           (in_BX[(int)(unaff_SI + 1)] - cVar14) - CARRY2(extraout_DX,(uint)in_BX);
      goto LAB_2000_3f08;
    }
  }
  else {
    iVar10 = *(int *)0x537e;
    *(int *)0x53e0 = iVar10 + -3;
    puVar12 = (undefined1 *)((iVar10 + -3) * 8);
    uVar13 = (undefined2)((ulong)*(undefined4 *)(unaff_BP + 10) >> 0x10);
    in_BX = (byte *)(byte *)*(undefined4 *)(unaff_BP + 10);
    pbVar7 = in_BX + (int)puVar12;
    *(undefined2 *)0x53a4 = *(undefined2 *)(pbVar7 + -8);
    *(undefined2 *)0x53a6 = *(undefined2 *)(pbVar7 + -6);
    *(undefined2 *)0x53a8 = *(undefined2 *)(pbVar7 + -4);
    *(undefined2 *)0x53aa = *(undefined2 *)(pbVar7 + -2);
    pcVar4 = (code *)swi(0x39);
    (*pcVar4)();
    pbVar7 = (byte *)0x53ad;
    *(undefined1 *)0x53ac = *puVar12;
    pcVar4 = (code *)swi(0x38);
    (*pcVar4)();
    pcVar4 = (code *)swi(0x39);
    (*pcVar4)();
    pcVar4 = (code *)swi(0x38);
    (*pcVar4)();
  }
  pcVar4 = (code *)swi(0x3d);
  (*pcVar4)();
  *(undefined2 *)0x537c = 1;
  if (3 < *(int *)0x537c) {
    *(undefined2 *)0x537c = 1;
    pcVar4 = (code *)swi(0x39);
    (*pcVar4)();
    pcVar4 = (code *)swi(0x38);
    (*pcVar4)();
    pcVar4 = (code *)swi(0x38);
    (*pcVar4)();
    *in_BX = *in_BX & (byte)((uint)in_BX >> 8);
    pcVar4 = (code *)swi(0x3a);
    (*pcVar4)();
    FUN_2000_79e0();
    return;
  }
  pcVar4 = (code *)swi(0x35);
  uVar5 = (*pcVar4)();
  out(extraout_DX_00,uVar5);
  pcVar4 = (code *)swi(0x39);
  (*pcVar4)();
  pcVar4 = (code *)swi(0x3d);
  (*pcVar4)();
  if (*(int *)*(undefined4 *)(unaff_BP + 6) != 0) {
    *(undefined2 *)0x5388 = 1;
    while (*(int *)0x5388 < 4) {
      iVar10 = *(int *)0x537c;
      pbVar7 = (byte *)(*(int *)0x537e * 0x18);
      iVar8 = *(int *)0x5388 << 3;
      bVar6 = *(int *)0x5388 << 2 < 0;
      pcVar4 = (code *)swi(0x39);
      (*pcVar4)();
      piVar3 = (int *)(iVar8 + iVar10 * 8 + 0x3c);
      *piVar3 = *piVar3 + 0x18b8 + (uint)bVar6;
      pbVar7[unaff_BP + -0x75] = extraout_DL;
      pcVar4 = (code *)swi(0x38);
      (*pcVar4)();
      pcVar4 = (code *)swi(0x3d);
      (*pcVar4)();
      *(int *)0x5388 = *(int *)0x5388 + 1;
    }
    *(undefined2 *)0x5388 = 4;
  }
LAB_2000_3f08:
  iVar10 = *(int *)0x537c;
  iVar8 = (int)((long)*(int *)0x537e * 0x18);
  cVar14 = (long)iVar8 != (long)*(int *)0x537e * 0x18;
  pcVar4 = (code *)swi(0x39);
  (*pcVar4)();
  pcVar2 = (char *)(iVar8 + iVar10 * 8 + 0x3c);
  *pcVar2 = *pcVar2 + -0x3c + cVar14;
  pcVar4 = (code *)swi(0x3c);
  (*pcVar4)();
  pcVar4 = (code *)swi(0x39);
  iVar10 = (*pcVar4)();
  pbVar7[unaff_BP + 4] = extraout_DL_00;
  pcVar2 = (char *)(iVar8 + in_stack_0000000e + 0x18);
  *pcVar2 = *pcVar2 + (char)((uint)iVar8 >> 8);
  *(int *)(unaff_BP + -4) = iVar10 * *(int *)0x537e;
  iVar10 = *(int *)0x537c;
  *(int *)(unaff_BP + -6) = iVar10 * 8;
  iVar8 = iVar10 * 8 + 0x3ff0;
  iVar9 = *(int *)(unaff_BP + -4) + 0x3c58;
  *(undefined2 *)(unaff_BP + -0xc) = 3;
  iVar10 = *(int *)(unaff_BP + -0xc);
  do {
    iVar11 = *(int *)(unaff_BP + -6);
    pcVar4 = (code *)swi(0x39);
    (*pcVar4)();
    pcVar4 = (code *)swi(0x38);
    (*pcVar4)();
    LOCK();
    piVar3 = (int *)(iVar11 + iVar8 + -0x32ad);
    iVar11 = *piVar3;
    *piVar3 = iVar9;
    UNLOCK();
    pcVar4 = (code *)swi(0x3d);
    (*pcVar4)();
    iVar8 = iVar8 + 0x18;
    iVar9 = iVar11 + 8;
    iVar10 = iVar10 + -1;
  } while (iVar10 != 0);
  pcVar4 = (code *)swi(0x39);
  (*pcVar4)();
  pcVar4 = (code *)swi(0x38);
  (*pcVar4)();
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}

