
void __stdcall16far
FUN_3000_e310(uint *param_1,undefined4 param_2,undefined4 param_3,undefined4 param_4)

{
  uint *puVar1;
  int *piVar2;
  uint uVar3;
  uint uVar4;
  undefined2 *puVar5;
  undefined2 *puVar6;
  int iVar7;
  int iVar8;
  uint uVar9;
  undefined2 *puVar10;
  undefined2 *puVar11;
  int iVar12;
  int iVar13;
  undefined2 uVar14;
  undefined2 uVar15;
  undefined2 uVar16;
  undefined2 uVar17;
  undefined2 unaff_DS;
  undefined4 local_8;
  
  *(undefined2 *)0x61f2 = 1;
  *(undefined2 *)0x61f4 = 0;
  while (((uVar14 = (undefined2)((ulong)param_4 >> 0x10), iVar12 = (int)param_4,
          *(int *)(iVar12 + *(int *)0x61f2 * 4 + -4) != 0 ||
          *(int *)(iVar12 + *(int *)0x61f2 * 4 + -2) != 0 && (*(int *)0x61f4 < 1)) &&
         ((*(int *)0x61f4 < 0 || (*(uint *)0x61f2 < 0xc9))))) {
    puVar1 = (uint *)0x61f2;
    uVar3 = *puVar1;
    *puVar1 = *puVar1 + 1;
    *(int *)0x61f4 = *(int *)0x61f4 + (uint)(0xfffe < uVar3);
  }
  uVar15 = (undefined2)((ulong)param_1 >> 0x10);
  iVar13 = *(int *)0x61f2;
  iVar7 = *(int *)0x61f4;
  *param_1 = iVar13 - 1;
  ((uint *)param_1)[1] = iVar7 - (uint)(iVar13 == 0);
  *(undefined2 *)0x61f2 = 1;
  *(undefined2 *)0x61f4 = 0;
  while (((uVar16 = (undefined2)((ulong)param_3 >> 0x10), iVar13 = (int)param_3,
          *(int *)(iVar13 + *(int *)0x61f2 * 4 + -4) != 0 ||
          *(int *)(iVar13 + *(int *)0x61f2 * 4 + -2) != 0 && (*(int *)0x61f4 < 1)) &&
         ((*(int *)0x61f4 < 0 || (*(uint *)0x61f2 < 0xc9))))) {
    puVar1 = (uint *)0x61f2;
    uVar3 = *puVar1;
    *puVar1 = *puVar1 + 1;
    *(int *)0x61f4 = *(int *)0x61f4 + (uint)(0xfffe < uVar3);
  }
  iVar7 = *(int *)0x61f2;
  iVar8 = *(int *)0x61f4;
  *(int *)0x61f6 = iVar7;
  *(int *)0x61f8 = iVar8;
  if ((-1 < iVar8) && ((0 < iVar8 || (iVar7 != 0)))) {
    uVar3 = *param_1;
    local_8 = (undefined2 *)CONCAT22(uVar16,(undefined2 *)(*(int *)0x61f2 * 4 + iVar13 + -4));
    do {
      uVar17 = (undefined2)((ulong)local_8 >> 0x10);
      uVar16 = ((undefined2 *)local_8)[1];
      iVar13 = (uVar3 + *(int *)0x61f2) * 4;
      *(undefined2 *)((int)param_2 + iVar13 + -4) = *local_8;
      *(undefined2 *)((int)param_2 + iVar13 + -2) = uVar16;
      local_8 = (undefined2 *)CONCAT22(uVar17,(undefined2 *)local_8 + -2);
      piVar2 = (int *)0x61f2;
      iVar13 = *piVar2;
      *piVar2 = *piVar2 + -1;
      *(int *)0x61f4 = *(int *)0x61f4 + -1 + (uint)(iVar13 != 0);
      if (*(int *)0x61f4 < 0) break;
    } while ((0 < *(int *)0x61f4) || (*(int *)0x61f2 != 0));
  }
  uVar3 = *param_1;
  uVar9 = ((uint *)param_1)[1];
  *(undefined2 *)0x61f2 = 1;
  *(undefined2 *)0x61f4 = 0;
  if ((-1 < (int)uVar9) && ((0 < (int)uVar9 || (uVar3 != 0)))) {
    puVar10 = (undefined2 *)(*(int *)0x61f2 * 4 + (int)param_2 + -4);
    puVar11 = (undefined2 *)(*(int *)0x61f2 * 4 + iVar12 + -4);
    for (iVar12 = uVar3 << 1; iVar12 != 0; iVar12 = iVar12 + -1) {
      puVar6 = puVar10;
      puVar10 = puVar10 + 1;
      puVar5 = puVar11;
      puVar11 = puVar11 + 1;
      *puVar6 = *puVar5;
    }
    puVar1 = (uint *)0x61f2;
    uVar4 = *puVar1;
    *puVar1 = *puVar1 + uVar3;
    *(int *)0x61f4 = *(int *)0x61f4 + uVar9 + (uint)CARRY2(uVar4,uVar3);
  }
  return;
}

