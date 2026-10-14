
/* WARNING: Instruction at (ram,0x0001b3bf) overlaps instruction at (ram,0x0001b3be)
    */
/* WARNING: Control flow encountered bad instruction data */

void FUN_1000_babf(void)

{
  uint *puVar1;
  uint uVar2;
  code *pcVar3;
  int *piVar4;
  undefined1 uVar5;
  undefined1 uVar6;
  int iVar7;
  int iVar8;
  uint uVar9;
  undefined1 extraout_AH;
  byte bVar10;
  int iVar11;
  undefined2 extraout_DX;
  int *piVar12;
  undefined2 *puVar13;
  undefined2 *puVar14;
  undefined2 *unaff_BP;
  int iVar15;
  int iVar16;
  undefined2 uVar17;
  undefined2 uVar18;
  undefined2 unaff_SS;
  undefined2 unaff_DS;
  bool bVar19;
  char cVar20;
  char cVar21;
  bool bVar22;
  longdouble lVar23;
  undefined4 uVar24;
  undefined2 in_stack_0000ccd6;
  
  *(int *)0x1944 = (int)(unaff_BP + -2);
  *(undefined2 *)0x1946 = unaff_SS;
  FUN_1000_4be9();
  *(undefined2 *)0x4cee = 0;
  *(undefined2 *)0x4cec = 0;
  if (*(int *)0x39d0 != 0 || *(int *)0x39d2 != 0) {
    uVar9 = *(uint *)0x4c88;
    iVar16 = *(int *)0x4c8a;
    uVar2 = *(uint *)0x39d0;
    iVar11 = *(int *)0x39d2;
    *(int *)0x4cec = uVar9 * 10 + *(uint *)0x39d0;
    *(int *)0x4cee =
         ((((iVar16 << 1 | (uint)((int)uVar9 < 0)) << 1 | (uint)((int)(uVar9 << 1) < 0)) + iVar16 +
          (uint)CARRY2(uVar9 * 4,uVar9)) * 2 | (uint)((int)(uVar9 * 5) < 0)) + iVar11 +
         (uint)CARRY2(uVar9 * 10,uVar2);
  }
  uVar18 = unaff_BP[6];
  iVar11 = *(int *)0x4c7c * 4;
  unaff_BP[-0x2c] = unaff_BP[5] + iVar11 + -4;
  unaff_BP[-0x2b] = uVar18;
  func_0x0002f3ee();
  uVar24 = FUN_2000_f48a();
  uVar9 = *(uint *)0x4cec;
  iVar16 = *(int *)0x4cee;
  piVar4 = *(int **)(unaff_BP + -0x2c);
  *piVar4 = (uint)uVar24 + *(uint *)0x4cec;
  ((int *)piVar4)[1] = (int)((ulong)uVar24 >> 0x10) + iVar16 + (uint)CARRY2((uint)uVar24,uVar9);
  if ((*(int *)0x39d2 < 1) && ((*(int *)0x39d2 < 0 || (*(uint *)0x39d0 < 5)))) {
    if ((*(int *)0x4ca2 < 1) && ((*(int *)0x4ca2 < 0 || (*(uint *)0x4ca0 < 0xb)))) {
      pcVar3 = (code *)swi(0x3c);
      (*pcVar3)();
      pcVar3 = (code *)swi(0x34);
      (*pcVar3)();
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    }
    if (((*(int *)0x39d0 != 0 || *(int *)0x39d2 != 0) && (*(int *)0x4c88 == 1)) &&
       (*(int *)0x4c8a == 0)) {
      FUN_1000_b5e9();
      return;
    }
    if (*(int *)0x39d0 == 0 && *(int *)0x39d2 == 0) {
      iVar16 = *(int *)((int)*(undefined4 *)(unaff_BP + 0x3b) + *(int *)0x4c9c * 2 + -2);
      iVar11 = CONCAT11((char)((uint)iVar11 >> 8),3);
      pcVar3 = (code *)swi(0x3c);
      (*pcVar3)();
      unaff_BP[-0x31] = iVar16;
      pcVar3 = (code *)swi(0x3b);
      (*pcVar3)();
      iVar15 = iVar16 + 1;
      uVar18 = 0x2e73;
      FUN_3000_2573();
      pcVar3 = (code *)swi(0x39);
      (*pcVar3)();
      pcVar3 = (code *)swi(0x3d);
      (*pcVar3)();
      piVar4 = *(int **)(unaff_BP + 0x61);
      if (*piVar4 == 0 && ((int *)piVar4)[1] == 0) {
        uVar18 = 0xff9;
        func_0x000128db();
      }
      piVar4 = *(int **)(unaff_BP + 0x61);
      if ((*piVar4 == 1) && (((int *)piVar4)[1] == 0)) {
        uVar18 = 0xff9;
        func_0x00012e5c();
      }
      cVar21 = false;
      cVar20 = *(int *)0x4c8a < 0;
      if (!(bool)cVar20) {
        if (*(int *)0x4c8a < 1) {
          uVar9 = *(uint *)0x4c88;
          cVar21 = SBORROW2(uVar9,1);
          cVar20 = (int)(uVar9 - 1) < 0;
          if (uVar9 < 2) goto LAB_1000_be4f;
        }
        pcVar3 = (code *)swi(0x39);
        (*pcVar3)();
        *(undefined2 *)(iVar16 + -0x74) = uVar18;
        in_stack_0000ccd6 = unaff_DS;
        if (cVar21 != cVar20) goto LAB_1000_be63;
        iVar15 = (int)*(undefined4 *)(unaff_BP + 0x1f);
        pcVar3 = (code *)swi(0x3c);
        (*pcVar3)();
        pcVar3 = (code *)swi(0x39);
        (*pcVar3)();
        pcVar3 = (code *)swi(0x3d);
        (*pcVar3)();
      }
LAB_1000_be4f:
      while (FUN_1000_cd62(), uVar17 = (undefined2)((ulong)*(undefined4 *)(unaff_BP + 0x5d) >> 0x10)
            , iVar16 = (int)*(undefined4 *)(unaff_BP + 0x5d),
            *(int *)(iVar16 + 0xc) == 0 && *(int *)(iVar16 + 0xe) == 0) {
LAB_1000_be63:
        cVar21 = *(int *)0x4c7c << 1 < 0;
        iVar15 = *(int *)0x4c7c << 2;
        pcVar3 = (code *)swi(0x35);
        cVar20 = (*pcVar3)();
        cVar20 = (char)(cVar20 + ':' + cVar21) == '\0';
        pcVar3 = (code *)swi(0x35);
        (*pcVar3)();
        iVar11 = iVar11 + -1;
        if (iVar11 == 0 || cVar20 != '\0') {
          return;
        }
      }
      uVar17 = (undefined2)((ulong)*(int **)(unaff_BP + 0x61) >> 0x10);
      piVar12 = (int *)*(int **)(unaff_BP + 0x61);
      do {
        if (*piVar12 != 0 || piVar12[1] != 0) goto LAB_1000_bec3;
        uVar17 = unaff_BP[0x2c];
        iVar11 = *(int *)0x4c7c * 4;
        iVar16 = ((*(int *)0x4c88 * unaff_BP[-0x20] + unaff_BP[0x2b]) - unaff_BP[-0x1f]) + iVar11;
        cVar20 = iVar16 == 0;
        unaff_BP[-0x2c] = iVar16;
        unaff_BP[-0x2b] = uVar17;
        uVar17 = (undefined2)((ulong)*(int **)(unaff_BP + -0x2c) >> 0x10);
        piVar12 = (int *)*(int **)(unaff_BP + -0x2c);
        pcVar3 = (code *)swi(0x3c);
        (*pcVar3)();
        pcVar3 = (code *)swi(0x35);
        (*pcVar3)();
        iVar11 = iVar11 + -1;
      } while (iVar11 != 0 && cVar20 == '\0');
      pcVar3 = (code *)swi(0x3d);
      (*pcVar3)();
      unaff_DS = in_stack_0000ccd6;
LAB_1000_bec3:
      uVar17 = (undefined2)((ulong)*(undefined4 *)(unaff_BP + 0x5d) >> 0x10);
      iVar16 = (int)*(undefined4 *)(unaff_BP + 0x5d);
      if ((*(int *)(iVar16 + 0xe) < 0) ||
         ((*(int *)(iVar16 + 0xe) < 1 && (*(uint *)(iVar16 + 0xc) < 2)))) {
        iVar8 = *(int *)0x4c8a;
        bVar22 = false;
        bVar19 = iVar8 == 0;
      }
      else {
        iVar16 = (*(int *)0x4c88 * unaff_BP[-0x20] + unaff_BP[0x2b]) - unaff_BP[-0x1f];
        iVar15 = *(int *)0x4c7c << 2;
        pcVar3 = (code *)swi(0x39);
        iVar7 = (*pcVar3)();
        bVar22 = SBORROW2(iVar7,0x3e83);
        iVar8 = iVar7 + -0x3e83;
        bVar19 = iVar7 == 0x3e83;
        iVar11 = (uint)(byte)(((char)((uint)iVar11 >> 8) - (char)iVar11) - ((byte)iVar7 < 0xd9)) <<
                 8;
      }
      if (!bVar19 && bVar22 == iVar8 < 0) {
        FUN_1000_b455();
        return;
      }
      if ((bVar22 == iVar8 < 0) && (1 < *(uint *)0x4c88)) {
        FUN_1000_b455();
        return;
      }
      pcVar3 = (code *)swi(0x39);
      (*pcVar3)();
      pcVar3 = (code *)swi(0x39);
      iVar8 = (*pcVar3)();
      if (iVar8 + -1 < 0x1e8b) {
        *(undefined2 *)(iVar16 + iVar15 + -2) = 0xf;
      }
      else {
        uVar24 = *(undefined4 *)(unaff_BP + 0x1f);
        pcVar3 = (code *)swi(0x39);
        (*pcVar3)();
        *(undefined2 *)((int)uVar24 + -0x33) = uVar18;
        pcVar3 = (code *)swi(0x3d);
        (*pcVar3)();
        uVar18 = (undefined2)((ulong)*(undefined4 *)(unaff_BP + 0x5d) >> 0x10);
        iVar16 = (int)*(undefined4 *)(unaff_BP + 0x5d);
        if (*(int *)(iVar16 + 0x1c) == 0 && *(int *)(iVar16 + 0x1e) == 0) {
          FUN_1000_b455();
          return;
        }
        if (*(int *)0x4d1a < 0) {
          FUN_1000_b3e1();
          return;
        }
        if ((*(int *)0x4d1a < 1) && (*(uint *)0x4d18 < 0x16)) {
          FUN_1000_b3e1();
          return;
        }
      }
      iVar16 = *(int *)0x4c7c;
      uVar18 = (undefined2)((ulong)*(undefined4 *)(unaff_BP + 5) >> 0x10);
      iVar15 = (int)*(undefined4 *)(unaff_BP + 5);
      *(undefined2 *)(iVar16 * 4 + iVar15 + -4) = 0x423f;
      *(undefined2 *)(iVar16 * 4 + iVar15 + -2) = 0xf;
    }
  }
LAB_1000_bff5:
  do {
    piVar4 = (int *)0x4c7c;
    iVar16 = *piVar4;
    *piVar4 = *piVar4 + 1;
    if (SCARRY2(iVar16,1)) {
      FUN_1000_c2d4();
      return;
    }
    if ((int)unaff_BP[-0x28] < *(int *)0x4c7c) {
      FUN_1000_c2d4();
      return;
    }
    if ((-1 < *(int *)0x4ca2) && ((0 < *(int *)0x4ca2 || (10 < *(uint *)0x4ca0)))) {
      uVar18 = (undefined2)((ulong)*(undefined4 *)(unaff_BP + 5) >> 0x10);
      iVar15 = (int)*(undefined4 *)(unaff_BP + 5);
      iVar16 = *(int *)(*(int *)0x4c7c * 4 + iVar15 + -2);
      if ((0 < iVar16) || ((-1 < iVar16 && (9999 < *(uint *)(*(int *)0x4c7c * 4 + iVar15 + -4)))))
      goto LAB_1000_bff5;
    }
    uVar18 = (undefined2)((ulong)*(undefined4 *)(unaff_BP + 5) >> 0x10);
    iVar16 = (int)*(undefined4 *)(unaff_BP + 5);
  } while (*(int *)(*(int *)0x4c7c * 4 + iVar16 + -4) == 0 &&
           *(int *)(*(int *)0x4c7c * 4 + iVar16 + -2) == 0);
  *(undefined2 *)0x4c7a = 1;
  do {
    uVar5 = (undefined1)((uint)iVar11 >> 8);
    iVar11 = CONCAT11(uVar5,3);
    iVar15 = *(int *)0x4c7a * 8;
    uVar18 = unaff_BP[4];
    iVar16 = *(int *)0x4c7c * 0xe8 + unaff_BP[3] + iVar15;
    *(undefined2 *)(iVar15 + 0x3a88) = *(undefined2 *)(iVar16 + -0xf0);
    *(undefined2 *)(iVar15 + 0x3a8a) = *(undefined2 *)(iVar16 + -0xee);
    *(undefined2 *)(iVar15 + 0x3a8c) = *(undefined2 *)(iVar16 + -0xec);
    *(undefined2 *)(iVar15 + 0x3a8e) = *(undefined2 *)(iVar16 + -0xea);
    *(int *)0x4c7a = *(int *)0x4c7a + 1;
  } while (*(int *)0x4c7a < 0x1e);
  *(undefined2 *)0x4d1a = 0;
  *(undefined2 *)0x4d18 = 0;
  bVar10 = 2;
  pcVar3 = (code *)swi(0x3c);
  (*pcVar3)();
  pcVar3 = (code *)swi(0x3c);
  (*pcVar3)();
  pcVar3 = (code *)swi(0x38);
  (*pcVar3)();
  pcVar3 = (code *)swi(0x38);
  uVar6 = (*pcVar3)();
  out(0x2d,uVar6);
  pcVar3 = (code *)swi(0x39);
  (*pcVar3)();
  pcVar3 = (code *)swi(0x3d);
  (*pcVar3)();
  pcVar3 = (code *)swi(0x3c);
  (*pcVar3)();
  pcVar3 = (code *)swi(0x3c);
  (*pcVar3)();
  pcVar3 = (code *)swi(0x38);
  (*pcVar3)();
  pcVar3 = (code *)swi(0x39);
  (*pcVar3)();
  pcVar3 = (code *)swi(0x3d);
  (*pcVar3)();
  pcVar3 = (code *)swi(0x3c);
  (*pcVar3)();
  pcVar3 = (code *)swi(0x38);
  (*pcVar3)();
  pcVar3 = (code *)swi(0x35);
  (*pcVar3)();
  *(byte *)(iVar15 + 0x3a5d) = *(byte *)(iVar15 + 0x3a5d) | bVar10;
  pcVar3 = (code *)swi(0x38);
  (*pcVar3)();
  pcVar3 = (code *)swi(0x35);
  (*pcVar3)();
  *(char *)(iVar15 + 0x3a5d) = *(char *)(iVar15 + 0x3a5d) + bVar10;
  pcVar3 = (code *)swi(0x38);
  (*pcVar3)();
  pcVar3 = (code *)swi(0x38);
  uVar6 = (*pcVar3)();
  out(0x2d,uVar6);
  func_0x000325d9();
  pcVar3 = (code *)swi(0x39);
  (*pcVar3)();
  pcVar3 = (code *)swi(0x3d);
  (*pcVar3)();
  uVar9 = *(uint *)0x4ca0;
  iVar16 = *(int *)0x4ca2;
  if (iVar16 < 0) {
    bVar19 = uVar9 != 0;
    uVar9 = -uVar9;
    iVar16 = -(iVar16 + (uint)bVar19);
  }
  if ((iVar16 < 1) && ((iVar16 < 0 || (uVar9 < 0xb)))) {
    uVar18 = *(undefined2 *)0x4cba;
    unaff_BP[-0x2a] = *(undefined2 *)0x4cb8;
    unaff_BP[-0x29] = uVar18;
    *(undefined2 *)0x4c88 = 1;
    *(undefined2 *)0x4c8a = 0;
    do {
      if (((int)unaff_BP[-0x29] < *(int *)0x4c8a) ||
         (((int)unaff_BP[-0x29] <= *(int *)0x4c8a && ((uint)unaff_BP[-0x2a] < *(uint *)0x4c88))))
      break;
      uVar18 = unaff_BP[0x2a];
      unaff_BP[-0x2c] = (*(int *)0x4c88 * unaff_BP[-0x1e] + unaff_BP[0x29]) - unaff_BP[-0x1d];
      unaff_BP[-0x2b] = uVar18;
      iVar16 = *(int *)0x4c32 << 2;
      uVar24 = *(undefined4 *)(unaff_BP + -0x2c);
      pcVar3 = (code *)swi(0x3c);
      (*pcVar3)();
      lVar23 = (longdouble)*(float *)(iVar16 + (int)uVar24);
      pcVar3 = (code *)swi(0x38);
      (*pcVar3)();
      iVar11 = CONCAT11(extraout_AH,0x4c);
      iVar16 = *(int *)0x4c7c;
      pcVar3 = (code *)swi(0x3c);
      (*pcVar3)();
      *(float *)(iVar11 + iVar16 * 4) = (float)lVar23;
      pcVar3 = (code *)swi(0x3d);
      (*pcVar3)();
      uVar18 = unaff_BP[0x28];
      unaff_BP[-0x2c] = (*(int *)0x4c88 * unaff_BP[-0x1c] + unaff_BP[0x27]) - unaff_BP[-0x1b];
      unaff_BP[-0x2b] = uVar18;
      iVar16 = *(int *)0x4c32 << 2;
      uVar24 = *(undefined4 *)(unaff_BP + -0x2c);
      pcVar3 = (code *)swi(0x3c);
      (*pcVar3)();
      lVar23 = (longdouble)*(float *)(iVar16 + (int)uVar24);
      pcVar3 = (code *)swi(0x38);
      iVar11 = (*pcVar3)();
      iVar16 = *(int *)0x4c7c;
      pcVar3 = (code *)swi(0x3c);
      (*pcVar3)();
      *(float *)(iVar11 + iVar16 * 4) = (float)lVar23;
      pcVar3 = (code *)swi(0x3d);
      (*pcVar3)();
      puVar1 = (uint *)0x4c88;
      uVar9 = *puVar1;
      *puVar1 = *puVar1 + 1;
      iVar16 = *(int *)0x4c8a;
      *(int *)0x4c8a = iVar16 + (uint)(0xfffe < uVar9);
    } while (!SCARRY2(iVar16,(uint)(0xfffe < uVar9)));
  }
  pcVar3 = (code *)swi(0x3c);
  (*pcVar3)();
  pcVar3 = (code *)swi(0x38);
  (*pcVar3)();
  pcVar3 = (code *)swi(0x35);
  (*pcVar3)();
  pcVar3 = (code *)swi(0x3d);
  (*pcVar3)();
  uVar18 = *(undefined2 *)0x4cfe;
  *(undefined2 *)0x4cf0 = *(undefined2 *)0x4cfc;
  *(undefined2 *)0x4cf2 = uVar18;
  uVar18 = *(undefined2 *)0x4d02;
  *(undefined2 *)0x4cf4 = *(undefined2 *)0x4d00;
  *(undefined2 *)0x4cf6 = uVar18;
  pcVar3 = (code *)swi(0x35);
  uVar6 = (*pcVar3)();
  out(extraout_DX,uVar6);
  pcVar3 = (code *)swi(0x39);
  (*pcVar3)();
  pcVar3 = (code *)swi(0x3d);
  (*pcVar3)();
  iVar11 = CONCAT11(uVar5,3);
  uVar18 = (undefined2)((ulong)*(undefined4 *)(unaff_BP + 0x45) >> 0x10);
  iVar16 = *(int *)0x4c7c * 8 + (int)*(undefined4 *)(unaff_BP + 0x45);
  *(undefined2 *)0x4c72 = *(undefined2 *)(iVar16 + -8);
  *(undefined2 *)0x4c74 = *(undefined2 *)(iVar16 + -6);
  *(undefined2 *)0x4c76 = *(undefined2 *)(iVar16 + -4);
  *(undefined2 *)0x4c78 = *(undefined2 *)(iVar16 + -2);
  uVar18 = (undefined2)((ulong)*(undefined4 *)(unaff_BP + 0x3d) >> 0x10);
  iVar16 = (int)*(undefined4 *)(unaff_BP + 0x3d) + **(int **)(unaff_BP + 0x65) * 8;
  *(undefined2 *)(iVar16 + -8) = *(undefined2 *)&DAT_0000_3b10;
  *(undefined2 *)(iVar16 + -6) = *(undefined2 *)&DAT_0000_3b12;
  *(undefined2 *)(iVar16 + -4) = *(undefined2 *)0x3b14;
  *(undefined2 *)(iVar16 + -2) = *(undefined2 *)0x3b16;
  uVar9 = *(uint *)0x39d8;
  iVar16 = *(int *)0x39da;
  *(int *)0x39e0 = -4 - *(uint *)0x39d8;
  *(int *)0x39e2 = (-1 - iVar16) - (uint)(0xfffc < uVar9);
  if (*(int *)0x39d8 == 0 && *(int *)0x39da == 0) {
    *(undefined2 *)0x39e0 = 0xffff;
    *(undefined2 *)0x39e2 = 0xffff;
  }
  piVar4 = *(int **)(unaff_BP + 99);
  if ((*piVar4 == 99) && (((int *)piVar4)[1] == 0)) {
    FUN_1000_b240();
    return;
  }
  *(undefined2 *)0x4ce8 = 1;
  *(undefined2 *)0x4cea = 0;
  *(undefined2 *)0x39fc = 0xffff;
  *(undefined2 *)0x39fe = 0xffff;
  puVar14 = unaff_BP;
  if ((*(int *)0x4ca2 < 1) && ((*(int *)0x4ca2 < 0 || (*(uint *)0x4ca0 < 0xb)))) {
    piVar4 = *(int **)(unaff_BP + 0x5f);
    if (*piVar4 == 0 && ((int *)piVar4)[1] == 0) {
      FUN_1000_20ca();
      piVar4 = *(int **)(unaff_BP + 99);
      if ((*piVar4 == 99) && (((int *)piVar4)[1] == 0)) {
        pcVar3 = (code *)swi(0x39);
        (*pcVar3)();
        puVar13 = (undefined2 *)&stack0xffe8;
        puVar14 = (undefined2 *)&stack0xffe8;
        cVar20 = '\x17';
        do {
          unaff_BP = unaff_BP + -1;
          puVar13 = puVar13 + -1;
          *puVar13 = *unaff_BP;
          cVar20 = cVar20 + -1;
        } while ('\0' < cVar20);
        pcVar3 = (code *)swi(0x39);
        (*pcVar3)();
        pcVar3 = (code *)swi(0x38);
        (*pcVar3)();
        pcVar3 = (code *)swi(0x38);
        (*pcVar3)();
        pcVar3 = (code *)swi(0x39);
        (*pcVar3)();
        pcVar3 = (code *)swi(0x38);
        (*pcVar3)();
        pcVar3 = (code *)swi(0x38);
        (*pcVar3)();
        pcVar3 = (code *)swi(0x38);
        (*pcVar3)();
        pcVar3 = (code *)swi(0x39);
        (*pcVar3)();
        pcVar3 = (code *)swi(0x39);
        (*pcVar3)();
        cVar20 = &stack0x0000 == (undefined1 *)0xcd73;
        pcVar3 = (code *)swi(0x38);
        uVar5 = (*pcVar3)();
        out(0x2d,uVar5);
        func_0x000325d9();
        pcVar3 = (code *)swi(0x3a);
        (*pcVar3)();
        pcVar3 = (code *)swi(0x39);
        (*pcVar3)();
        if (iVar11 != 1 && cVar20 == '\0') goto code_r0x0001b3b7;
        pcVar3 = (code *)swi(0x3d);
        (*pcVar3)();
        *(undefined2 *)0x3a90 = *(undefined2 *)0x4ce0;
        *(undefined2 *)0x3a92 = *(undefined2 *)0x4ce2;
        *(undefined2 *)0x3a94 = *(undefined2 *)0x4ce4;
        *(undefined2 *)0x3a96 = *(undefined2 *)0x4ce6;
        puVar14 = (undefined2 *)&stack0xffe8;
      }
    }
    else {
      func_0x0001226c();
    }
  }
  *(undefined2 *)0x4c7a = 1;
  do {
    iVar11 = *(int *)0x4c7a * 8;
    uVar18 = puVar14[4];
    iVar16 = *(int *)0x4c7c * 0xe8 + puVar14[3] + iVar11;
    *(undefined2 *)(iVar16 + -0xf0) = *(undefined2 *)(iVar11 + 0x3a88);
    *(undefined2 *)(iVar16 + -0xee) = *(undefined2 *)(iVar11 + 0x3a8a);
    *(undefined2 *)(iVar16 + -0xec) = *(undefined2 *)(iVar11 + 0x3a8c);
    *(undefined2 *)(iVar16 + -0xea) = *(undefined2 *)(iVar11 + 0x3a8e);
    *(int *)0x4c7a = *(int *)0x4c7a + 1;
  } while (*(int *)0x4c7a < 0x1e);
code_r0x0001b3b7:
  uVar18 = *(undefined2 *)0x4cea;
  *(undefined2 *)0x4d14 = *(undefined2 *)0x4ce8;
  *(undefined2 *)0x4d16 = uVar18;
  uVar18 = *(undefined2 *)0x4cba;
  puVar14[-0x30] = *(undefined2 *)0x4cb8;
  puVar14[-0x2f] = uVar18;
  *(undefined2 *)0x4c88 = 1;
  *(undefined2 *)0x4c8a = 0;
  FUN_1000_b9fc();
  return;
}

