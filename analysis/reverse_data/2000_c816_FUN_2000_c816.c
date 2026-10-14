
void FUN_2000_c816(undefined2 param_1,undefined2 param_2,undefined2 param_3,undefined2 param_4,
                  undefined2 param_5,undefined2 param_6,undefined2 param_7,undefined2 param_8,
                  undefined2 param_9,undefined2 param_10,undefined2 param_11,undefined2 param_12,
                  undefined2 param_13,undefined2 param_14,undefined2 param_15,undefined2 param_16,
                  undefined2 param_17,undefined2 param_18,undefined2 param_19)

{
  int iVar1;
  undefined2 uVar2;
  uint uVar3;
  undefined2 *puVar4;
  uint uVar5;
  uint uVar6;
  int iVar7;
  int iVar8;
  int iVar9;
  undefined2 uVar10;
  undefined2 uVar11;
  undefined2 unaff_SS;
  undefined2 unaff_DS;
  undefined4 uVar12;
  undefined2 uStack_8;
  undefined2 uStack_6;
  undefined2 local_4;
  
  iVar1 = *(int *)0x1944;
  uVar2 = *(undefined2 *)0x1946;
  *(undefined2 *)0x5a82 = param_18;
  *(undefined2 *)0x5a84 = param_19;
  *(undefined2 *)0x5a86 = param_16;
  *(undefined2 *)0x5a88 = param_17;
  *(undefined2 *)0x5a8a = param_14;
  *(undefined2 *)0x5a8c = param_15;
  *(undefined2 *)0x5a8e = param_12;
  *(undefined2 *)0x5a90 = param_13;
  *(undefined2 *)0x5a92 = param_10;
  *(undefined2 *)0x5a94 = param_11;
  *(undefined2 *)0x5a96 = param_8;
  *(undefined2 *)0x5a98 = param_9;
  *(undefined2 *)0x5a9a = param_6;
  *(undefined2 *)0x5a9c = param_7;
  *(undefined2 *)0x5a9e = param_4;
  *(undefined2 *)0x5aa0 = param_5;
  *(undefined2 *)0x5aa2 = param_2;
  *(undefined2 *)0x5aa4 = param_3;
  local_4 = 0;
  if (*(int *)0x75a == 2) {
    FUN_3000_37ee(0x40,0,0x5269,0x10);
    *(undefined2 *)0x75a = 1;
  }
  *(undefined2 *)*(undefined4 *)0x5a82 = *(undefined2 *)*(undefined4 *)0x5a86;
  *(undefined2 *)((int)*(undefined4 *)0x5a82 + 2) = *(undefined2 *)*(undefined4 *)0x5a8a;
  *(int *)((int)*(undefined4 *)0x5a82 + 4) =
       *(int *)*(undefined4 *)0x5a86 + *(int *)*(undefined4 *)0x5a8e + -1;
  *(int *)((int)*(undefined4 *)0x5a82 + 6) =
       *(int *)*(undefined4 *)0x5a8a + *(int *)*(undefined4 *)0x5a92 + -1;
  if (*(char *)*(undefined4 *)0x5a96 == *(char *)0x759) {
    iVar8 = *(int *)*(undefined4 *)0x5a8e;
    uVar10 = (undefined2)((ulong)*(undefined4 *)0x5a82 >> 0x10);
    iVar7 = (int)*(undefined4 *)0x5a82;
    *(int *)(iVar7 + 8) = iVar8;
    *(int *)(iVar7 + 10) = iVar8 >> 0xf;
    iVar8 = *(int *)*(undefined4 *)0x5a92;
    iVar7 = iVar8 >> 0xf;
  }
  else {
    uVar5 = *(uint *)*(undefined4 *)0x5a8e;
    uVar10 = (undefined2)((ulong)*(undefined4 *)0x5a82 >> 0x10);
    iVar8 = (int)*(undefined4 *)0x5a82;
    *(int *)(iVar8 + 8) = uVar5 - 2;
    *(int *)(iVar8 + 10) = ((int)uVar5 >> 0xf) - (uint)(uVar5 < 2);
    uVar5 = *(uint *)*(undefined4 *)0x5a92;
    iVar8 = uVar5 - 2;
    iVar7 = ((int)uVar5 >> 0xf) - (uint)(uVar5 < 2);
  }
  uVar10 = (undefined2)((ulong)*(undefined4 *)0x5a82 >> 0x10);
  iVar9 = (int)*(undefined4 *)0x5a82;
  *(int *)(iVar9 + 0xc) = iVar8;
  *(int *)(iVar9 + 0xe) = iVar7;
  puVar4 = (undefined2 *)*(undefined4 *)0x5aa2;
  uVar10 = ((undefined2 *)puVar4)[1];
  uVar11 = (undefined2)((ulong)*(undefined4 *)0x5a82 >> 0x10);
  iVar8 = (int)*(undefined4 *)0x5a82;
  *(undefined2 *)(iVar8 + 0x14) = *puVar4;
  *(undefined2 *)(iVar8 + 0x16) = uVar10;
  iVar8 = *(int *)(iVar1 + 4);
  *(int *)0x5ace = iVar8;
  *(int *)0x5ad0 = iVar8 >> 0xf;
  if (((iVar8 == 1) && (*(char *)*(undefined4 *)0x5a9a == *(char *)0x758)) ||
     (*(char *)*(undefined4 *)0x5a96 == *(char *)0x757)) {
    *(undefined2 *)0x5ad0 = 0;
    *(undefined2 *)0x5ace = 0;
  }
  if (*(int *)0x34ea == 0) {
    if (*(int *)0x75a == 0) {
      *(undefined2 *)0x5abe = 1;
      *(undefined2 *)0x5ac0 = 0;
      *(undefined2 *)0x5aba = 4000;
      *(undefined2 *)0x5abc = 0;
      uVar5 = *(uint *)0x5aba;
      iVar8 = *(int *)0x5abc;
      uVar3 = *(uint *)0x5abe;
      uVar6 = uVar5 - *(uint *)0x5abe;
      iVar7 = *(int *)0x5ac0;
      *(int *)0x5ab6 = uVar6 + 1;
      *(int *)0x5ab8 = ((iVar8 - iVar7) - (uint)(uVar5 < uVar3)) + (uint)(0xfffe < uVar6);
      uVar10 = *(undefined2 *)0x5ac0;
      *(undefined2 *)0x5ac2 = *(undefined2 *)0x5abe;
      *(undefined2 *)0x5ac4 = uVar10;
      iVar8 = FUN_3000_36e4();
      *(int *)0x5ad6 = iVar8;
      *(int *)0x5ad8 = iVar8 >> 0xf;
    }
    else {
      *(undefined2 *)0x5aae = 1;
      *(undefined2 *)0x5ab0 = 0;
      *(undefined2 *)0x5aaa = 4000;
      *(undefined2 *)0x5aac = 0;
      uVar5 = *(uint *)0x5aaa;
      iVar8 = *(int *)0x5aac;
      uVar3 = *(uint *)0x5aae;
      uVar6 = uVar5 - *(uint *)0x5aae;
      iVar7 = *(int *)0x5ab0;
      *(int *)0x5aa6 = uVar6 + 1;
      *(int *)0x5aa8 = ((iVar8 - iVar7) - (uint)(uVar5 < uVar3)) + (uint)(0xfffe < uVar6);
      uVar10 = *(undefined2 *)0x5ab0;
      *(undefined2 *)0x5ab2 = *(undefined2 *)0x5aae;
      *(undefined2 *)0x5ab4 = uVar10;
      iVar8 = FUN_3000_36e4();
      *(int *)0x5ac6 = iVar8;
      *(int *)0x5ac8 = iVar8 >> 0xf;
    }
    if (iVar8 == 0) {
      uVar10 = func_0x00020ac2();
      *(undefined2 *)0x5ade = uVar10;
    }
  }
  else {
    uVar12 = FUN_2000_0bf5();
    iVar8 = (int)((ulong)uVar12 >> 0x10);
    uVar5 = (uint)uVar12;
    *(uint *)0x5aca = uVar5;
    *(int *)0x5acc = iVar8;
    if (*(int *)0x75a == 0) {
      *(undefined2 *)0x5abe = 1;
      *(undefined2 *)0x5ac0 = 0;
      *(uint *)0x5aba = uVar5;
      *(int *)0x5abc = iVar8;
      uVar3 = *(uint *)0x5abe;
      uVar6 = uVar5 - *(uint *)0x5abe;
      iVar7 = *(int *)0x5ac0;
      *(int *)0x5ab6 = uVar6 + 1;
      *(int *)0x5ab8 = ((iVar8 - iVar7) - (uint)(uVar5 < uVar3)) + (uint)(0xfffe < uVar6);
      uVar10 = *(undefined2 *)0x5ac0;
      *(undefined2 *)0x5ac2 = *(undefined2 *)0x5abe;
      *(undefined2 *)0x5ac4 = uVar10;
      local_4 = 0xc0;
      uStack_6 = 0x1f78;
      uStack_8 = 0xcbaf;
      iVar8 = FUN_3000_36e4();
      *(int *)0x5ad6 = iVar8;
      *(int *)0x5ad8 = iVar8 >> 0xf;
    }
    else {
      *(undefined2 *)0x5aae = 1;
      *(undefined2 *)0x5ab0 = 0;
      uVar5 = *(uint *)0x5aca;
      iVar8 = *(int *)0x5acc;
      *(uint *)0x5aaa = uVar5;
      *(int *)0x5aac = iVar8;
      uVar3 = *(uint *)0x5aae;
      uVar6 = uVar5 - *(uint *)0x5aae;
      iVar7 = *(int *)0x5ab0;
      *(int *)0x5aa6 = uVar6 + 1;
      *(int *)0x5aa8 = ((iVar8 - iVar7) - (uint)(uVar5 < uVar3)) + (uint)(0xfffe < uVar6);
      uVar10 = *(undefined2 *)0x5ab0;
      *(undefined2 *)0x5ab2 = *(undefined2 *)0x5aae;
      *(undefined2 *)0x5ab4 = uVar10;
      local_4 = 0xc0;
      uStack_6 = 0x1f78;
      uStack_8 = 0xcc2e;
      iVar8 = FUN_3000_36e4();
      *(int *)0x5ac6 = iVar8;
      *(int *)0x5ac8 = iVar8 >> 0xf;
    }
    if (iVar8 == 0) {
      func_0x00039a2a();
    }
  }
  *(undefined2 *)0x5adc = 0;
  *(undefined2 *)0x5ada = 0;
  if (*(char *)*(undefined4 *)0x5a96 == *(char *)0x756) {
    *(undefined2 *)0x5ada = 100;
    *(undefined2 *)0x5adc = 0;
  }
  uVar11 = (undefined2)((ulong)*(undefined4 *)0x5a82 >> 0x10);
  iVar8 = (int)*(undefined4 *)0x5a82;
  uVar10 = *(undefined2 *)(iVar8 + 0x1a);
  *(undefined2 *)0x5ad2 = *(undefined2 *)(iVar8 + 0x18);
  *(undefined2 *)0x5ad4 = uVar10;
  iVar8 = *(int *)*(undefined4 *)0x5a9e;
  uVar10 = (undefined2)((ulong)*(undefined4 *)0x5a82 >> 0x10);
  iVar7 = (int)*(undefined4 *)0x5a82;
  *(int *)(iVar7 + 0x18) = iVar8;
  *(int *)(iVar7 + 0x1a) = iVar8 >> 0xf;
  uStack_6 = 1;
  *(int *)0x1944 = (int)&uStack_8;
  *(undefined2 *)0x1946 = unaff_SS;
  FUN_2000_6355();
  uVar11 = (undefined2)((ulong)*(undefined4 *)0x5a82 >> 0x10);
  iVar8 = (int)*(undefined4 *)0x5a82;
  uVar10 = *(undefined2 *)0x5ad4;
  *(undefined2 *)(iVar8 + 0x18) = *(undefined2 *)0x5ad2;
  *(undefined2 *)(iVar8 + 0x1a) = uVar10;
  if (*(int *)0x5ace != 0 || *(int *)0x5ad0 != 0) {
    uStack_6 = *(undefined2 *)(iVar1 + 4);
    *(int *)0x1944 = (int)&uStack_8;
    *(undefined2 *)0x1946 = unaff_SS;
    FUN_2000_5fff();
  }
  *(int *)0x75a = *(int *)0x75a + 1;
  FUN_2000_ceee();
  return;
}

