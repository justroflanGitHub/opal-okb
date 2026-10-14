
void __stdcall16far
FUN_2000_f782(int *param_1,undefined4 param_2,undefined2 param_3,undefined2 param_4,int param_5,
             undefined2 param_6,int *param_7,int *param_8)

{
  int *piVar1;
  int iVar2;
  undefined2 *puVar3;
  undefined2 *puVar4;
  undefined2 uVar5;
  int iVar6;
  int iVar7;
  int iVar8;
  int iVar9;
  int *piVar10;
  undefined2 unaff_SI;
  undefined2 *puVar12;
  undefined2 unaff_DI;
  undefined2 *puVar13;
  undefined2 uVar14;
  undefined2 uVar15;
  undefined2 unaff_SS;
  undefined2 unaff_DS;
  undefined2 uVar17;
  undefined2 uVar18;
  undefined2 uVar19;
  undefined2 uVar20;
  undefined2 uVar21;
  undefined2 uVar22;
  undefined2 uVar23;
  undefined2 uVar24;
  undefined2 uVar25;
  undefined2 uVar26;
  undefined2 uVar27;
  undefined2 uVar28;
  undefined2 uVar29;
  undefined2 uVar30;
  undefined2 uVar31;
  undefined2 uVar32;
  undefined2 uVar33;
  undefined2 uVar34;
  undefined1 local_c [2];
  undefined2 local_a;
  undefined2 local_8;
  int local_6;
  int *piVar11;
  undefined2 uVar16;
  
  iVar2 = *(int *)0x1944;
  uVar5 = *(undefined2 *)0x1946;
  iVar6 = *(int *)(iVar2 + 2);
  uVar14 = (undefined2)((ulong)param_2 >> 0x10);
  iVar9 = (int)param_2;
  *(undefined2 *)0x5d38 = *(undefined2 *)(iVar9 + 0x30);
  *(undefined2 *)(iVar9 + 0x32) = 0;
  *(undefined2 *)(iVar9 + 0x30) = 0;
  func_0x00031688(0x1000,0xa6c);
  *(undefined2 *)0x5d30 = 1;
  *(undefined2 *)0x5d1a = 1;
  do {
    iVar7 = FUN_3000_0772(0x2e73,0xa70,*(int *)0x5d30 * 0x33 + 0x24,0x506e);
    if (iVar7 < 0) break;
    if (*(char *)0x5d3a == *(char *)0xa6a) {
      uVar15 = *(undefined2 *)0x3154;
      *(undefined2 *)(*(int *)0x5d30 * 2 + 0x44c) = *(undefined2 *)0x5d1a;
      *(undefined1 *)(*(int *)0x5d30 * 0x33 + 0x23) = *(undefined1 *)0xa69;
      iVar7 = *(int *)0x5d30;
      uVar16 = *(undefined2 *)0x5d3d;
      *(undefined2 *)(iVar7 * 0x33 + 0x1f) = *(undefined2 *)0x5d3b;
      *(undefined2 *)(iVar7 * 0x33 + 0x21) = uVar16;
      *(int *)0x5d30 = *(int *)0x5d30 + 1;
      if (0x14 < *(int *)0x5d30) break;
    }
    *(int *)0x5d1a = *(int *)0x5d1a + 1;
  } while (*(int *)0x5d1a < 0x2711);
  piVar1 = (int *)0x5d30;
  *piVar1 = *piVar1 + -1;
  piVar10 = (int *)param_1;
  uVar15 = (undefined2)((ulong)param_1 >> 0x10);
  piVar11 = (int *)param_7;
  uVar16 = (undefined2)((ulong)param_7 >> 0x10);
  if (*piVar1 == 0) {
    piVar11[1] = 0;
    *param_7 = 0;
    *param_1 = 3;
    piVar10[1] = 0;
    func_0x00031688(0x2e73,0xa82);
    local_a = 0x19;
    *(int *)0x1944 = (int)local_c;
    *(undefined2 *)0x1946 = unaff_SS;
    func_0x00016191(0x2e73,0x388a);
  }
  else {
    uVar18 = *(undefined2 *)0x3154;
    puVar13 = (undefined2 *)0x0;
    puVar12 = (undefined2 *)0x369a;
    for (iVar7 = 0x29; iVar7 != 0; iVar7 = iVar7 + -1) {
      puVar4 = puVar13;
      puVar13 = puVar13 + 1;
      puVar3 = puVar12;
      puVar12 = puVar12 + 1;
      *puVar4 = *puVar3;
    }
    *(undefined2 *)0x5d14 = *(undefined2 *)0x385a;
    uVar20 = *(undefined2 *)0x38c0;
    *(undefined2 *)0x20 = *(undefined2 *)0x38be;
    *(undefined2 *)0x22 = uVar20;
    *(int *)0x5d16 = *(int *)0x3552 + -10;
    *(undefined2 *)0x5d40 = 0x12;
    *(undefined2 *)0x5d44 = 0x14;
    *(undefined2 *)0x5d34 = 0x2d;
    local_8 = 0x19;
    local_a = 1;
    uVar34 = 0x506e;
    uVar33 = 0;
    uVar31 = 0x5d16;
    uVar29 = 0x5d40;
    uVar27 = 0x5d44;
    uVar25 = 0x5d34;
    uVar23 = 0xa68;
    uVar22 = 0x54f7;
    uVar21 = 0x34;
    uVar19 = 0x5d14;
    uVar17 = 0x38c6;
    *(int *)0x1944 = (int)local_c;
    *(undefined2 *)0x1946 = unaff_SS;
    uVar18 = unaff_DS;
    uVar20 = unaff_DS;
    uVar24 = unaff_DS;
    uVar26 = unaff_DS;
    uVar28 = unaff_DS;
    uVar30 = unaff_DS;
    uVar32 = unaff_DS;
    FUN_1000_c816(0x2e73,0x38c6);
    *param_1 = 100;
    piVar10[1] = 0;
    iVar7 = *(int *)0x5d30;
    *(int *)0x5d1c = iVar7;
    *(int *)0x5d1e = iVar7 >> 0xf;
    *(undefined2 *)0x5d20 = 0x32;
    *(undefined2 *)0x5d22 = 0;
    *(undefined2 *)0x5d24 = 1;
    *(undefined2 *)0x5d26 = 0;
    *(undefined2 *)0x5d28 = 1;
    *(undefined2 *)0x5d2a = 0;
    *(undefined2 *)0x5d2c = 1;
    *(undefined2 *)0x5d2e = 0;
    do {
      while( true ) {
        local_a = 0x33;
        *(int *)0x1944 = (int)local_c;
        *(undefined2 *)0x1946 = unaff_SS;
        FUN_1000_d3bd(0x5d2c,unaff_DS,piVar10,uVar15,iVar9,uVar14,0x5d1c,unaff_DS,8,0x506e,0x52,
                      0x506e,uVar17,uVar18,uVar19,uVar20,uVar21,uVar22,uVar23,uVar24,uVar25,uVar26,
                      uVar27,uVar28,uVar29,uVar30,uVar31,uVar32,uVar33,uVar34,unaff_SI,unaff_DI);
        if ((*param_1 != 2) || (piVar10[1] != 0)) break;
        *(undefined2 *)0x5d42 = 1;
        local_8 = 7;
        local_a = 0xd;
        *(int *)0x1944 = (int)local_c;
        *(undefined2 *)0x1946 = unaff_SS;
        FUN_1000_e48c();
      }
    } while ((*param_1 == 5) && (piVar10[1] == 0));
    func_0x0001cd72();
    if ((((*param_1 == 1) && (piVar10[1] == 0)) || ((*param_1 == 0xb && (piVar10[1] == 0)))) ||
       ((((*param_1 == 3 && (piVar10[1] == 0)) || ((*param_1 == 4 && (piVar10[1] == 0)))) ||
        ((*param_1 == 7 && (piVar10[1] == 0)))))) {
      *param_1 = 3;
      piVar10[1] = 0;
      FUN_3000_17b6();
    }
    else {
      if ((*param_1 == 9) && (piVar10[1] == 0)) {
        *param_1 = 6;
        piVar10[1] = 0;
      }
      *(undefined2 *)0x5d48 = 0;
      if ((((*param_1 == 6) && (piVar10[1] == 0)) || ((*param_1 == 10 && (piVar10[1] == 0)))) ||
         ((*param_1 == 8 && (piVar10[1] == 0)))) {
        *(undefined2 *)0x5d48 = 1;
      }
      if ((((*param_1 == 0xc) && (piVar10[1] == 0)) || ((*param_1 == 6 && (piVar10[1] == 0)))) ||
         ((*param_1 == 8 && (piVar10[1] == 0)))) {
        func_0x00031688();
        if (*(int *)0x5d48 == 0) {
          iVar7 = *(int *)(*(int *)0x5d2c * 2 + 0x44c);
          *(undefined2 *)0x5d1a = 1;
          do {
            if (iVar7 < *(int *)0x5d1a) break;
            FUN_3000_0772();
            piVar1 = (int *)0x5d1a;
            iVar8 = *piVar1;
            *piVar1 = *piVar1 + 1;
          } while (!SCARRY2(iVar8,1));
        }
        *(undefined2 *)0x5d18 = 1;
        iVar7 = *param_8;
        *(undefined2 *)0x5d1a = 1;
        do {
          if (iVar7 < *(int *)0x5d1a) break;
          *(undefined2 *)0xaa7 = *(undefined2 *)(iVar2 + 2);
          local_6 = FUN_3000_0772();
          if (local_6 < 0) break;
          if ((*(int *)0x5d48 == 0) &&
             (*(char *)((*(int *)(iVar2 + 2) * *(int *)0x5d1a + param_5) - iVar6) == *(char *)0xa60)
             ) goto LAB_2000_fccf;
          if ((*(int *)0x5d48 != 0) &&
             ((*(char *)((*(int *)(iVar2 + 2) * *(int *)0x5d1a + param_5) - iVar6) == *(char *)0xa5f
              || (*(char *)((*(int *)(iVar2 + 2) * *(int *)0x5d1a + param_5) - iVar6) ==
                  *(char *)0xa5e)))) {
            *(undefined1 *)((*(int *)(iVar2 + 2) * *(int *)0x5d1a + param_5) - iVar6) =
                 *(undefined1 *)0xa5d;
          }
          local_a = *(undefined2 *)(iVar2 + 2);
          *(int *)0x1944 = (int)local_c;
          *(undefined2 *)0x1946 = unaff_SS;
          iVar8 = FUN_1000_c7b7();
          *(int *)0x5d36 = iVar8;
          if (*(int *)0x5d18 < iVar8) {
            *(int *)0x5d18 = iVar8;
          }
          piVar1 = (int *)0x5d1a;
          iVar8 = *piVar1;
          *piVar1 = *piVar1 + 1;
        } while (!SCARRY2(iVar8,1));
        FUN_3000_17b6();
LAB_2000_fccf:
        func_0x00032028();
        iVar6 = *(int *)0x5d1a;
        *param_7 = iVar6 + -1;
        piVar11[1] = (iVar6 >> 0xf) - (uint)(iVar6 == 0);
        iVar6 = *(int *)0x5d18;
        piVar11[2] = iVar6;
        piVar11[3] = iVar6 >> 0xf;
        piVar11[4] = 1;
        piVar11[5] = 0;
        piVar11[6] = 2;
        piVar11[7] = 0;
        if ((*param_1 != 8) || (piVar10[1] != 0)) {
          *param_1 = 0xe;
          piVar10[1] = 0;
        }
      }
      if ((*param_1 == 10) && (piVar10[1] == 0)) {
        local_8 = *(undefined2 *)(iVar2 + 4);
        local_a = *(undefined2 *)(iVar2 + 2);
        *(int *)0x1944 = (int)local_c;
        *(undefined2 *)0x1946 = unaff_SS;
        FUN_2000_ff74();
        if ((*param_1 != 1) || (piVar10[1] != 0)) {
          *param_1 = 3;
          piVar10[1] = 0;
          func_0x00031688();
          func_0x0002f5ce();
          return;
        }
        *param_1 = 3;
        piVar10[1] = 0;
      }
      else {
        thunk_FUN_1000_cf98();
      }
    }
  }
  iVar2 = *(int *)0x5d38;
  *(int *)(iVar9 + 0x30) = iVar2;
  *(int *)(iVar9 + 0x32) = iVar2 >> 0xf;
  return;
}

