
void __stdcall16far
FUN_3000_c975(undefined2 *param_1,undefined2 param_2,undefined2 *param_3,undefined2 param_4,
             undefined2 *param_5,undefined2 *param_6,undefined2 *param_7,int *param_8,
             undefined2 param_9,undefined2 param_10,int *param_11,int param_12,undefined2 param_13,
             int *param_14,int param_15,undefined2 param_16,int *param_17,uint *param_18,
             int *param_19)

{
  int iVar1;
  uint uVar2;
  undefined2 uVar3;
  bool bVar4;
  int iVar5;
  int iVar6;
  int iVar7;
  int iVar8;
  int iVar9;
  undefined2 *puVar10;
  int iVar11;
  int iVar12;
  undefined2 *puVar13;
  undefined2 *puVar14;
  undefined2 *puVar15;
  undefined2 uVar16;
  undefined2 unaff_DS;
  bool bVar17;
  undefined4 local_28;
  undefined4 local_1e;
  uint local_12;
  int local_10;
  uint local_e;
  int local_c;
  
  iVar11 = *param_14;
  iVar5 = iVar11 * 4;
  iVar6 = iVar5 + 4;
  iVar7 = *param_11 * 4;
  iVar8 = iVar7 + 4;
  *param_7 = 1;
  ((undefined2 *)param_7)[1] = 0;
  puVar13 = (undefined2 *)param_5;
  uVar16 = (undefined2)((ulong)param_5 >> 0x10);
  if ((((int *)param_19)[1] == 0) && (*param_19 == 1)) {
    uVar2 = *param_18;
    iVar11 = (int)uVar2 >> 0xf;
    local_12 = 2;
    local_10 = 0;
    if ((-1 < iVar11) && (((int)uVar2 < 0 || (1 < uVar2)))) {
      do {
        iVar1 = *param_17;
        iVar12 = (iVar1 >> 0xf) - (uint)(iVar1 == 0);
        local_e = 1;
        local_c = 0;
        if ((-1 < iVar12) && ((0 < iVar12 || (iVar1 != 1)))) {
          do {
            puVar10 = (undefined2 *)(((local_12 - 1) * iVar5 + local_e * 4 + param_15) - iVar6);
            local_1e = (undefined2 *)CONCAT22(param_16,puVar10);
            puVar14 = (undefined2 *)
                      (((*param_17 - local_e) * 4 + local_12 * iVar7 + param_12) - iVar8);
            uVar3 = puVar14[1];
            *local_1e = *puVar14;
            puVar10[1] = uVar3;
            FUN_3000_cc3a(puVar10,param_16,param_9,param_10);
            bVar17 = 0xfffe < local_e;
            local_e = local_e + 1;
            bVar4 = SCARRY2(local_c,(uint)bVar17);
            local_c = local_c + (uint)bVar17;
            if ((bVar4) || (iVar12 < local_c)) break;
          } while ((local_c < iVar12) || (local_e <= iVar1 - 1U));
        }
        bVar17 = 0xfffe < local_12;
        local_12 = local_12 + 1;
        bVar4 = SCARRY2(local_10,(uint)bVar17);
        local_10 = local_10 + (uint)bVar17;
      } while ((!bVar4) && ((local_10 <= iVar11 && ((local_10 < iVar11 || (local_12 <= uVar2))))));
    }
    *param_8 = *param_18 - 1;
    *param_6 = 0xffff;
    *param_5 = *param_3;
    puVar13[1] = param_3[1];
    puVar13[2] = param_3[2];
    puVar13[3] = param_3[3];
  }
  else if ((((int *)param_19)[1] == 0) && (*param_19 == 2)) {
    iVar1 = *param_17;
    iVar12 = (iVar1 >> 0xf) - (uint)(iVar1 == 0);
    local_e = 1;
    local_c = 0;
    if ((-1 < iVar12) && ((0 < iVar12 || (iVar1 != 1)))) {
      do {
        uVar2 = *param_18;
        iVar9 = (*param_17 - local_e) * 4;
        puVar10 = (undefined2 *)((local_e * 4 + iVar5 + param_15) - iVar6);
        local_28 = (undefined2 *)CONCAT22(param_16,puVar10);
        puVar14 = (undefined2 *)(((uVar2 + 1) * iVar7 + iVar9 + param_12) - iVar8);
        uVar3 = puVar14[1];
        *local_28 = *puVar14;
        puVar10[1] = uVar3;
        puVar14 = (undefined2 *)(((uVar2 + 2) * iVar7 + iVar9 + param_12) - iVar8);
        uVar3 = puVar14[1];
        puVar15 = (undefined2 *)((iVar11 * 8 + local_e * 4 + param_15) - iVar6);
        *puVar15 = *puVar14;
        puVar15[1] = uVar3;
        FUN_3000_cc3a(puVar10,param_16,param_9,param_10);
        FUN_3000_cc3a((local_e * 4 + iVar11 * 8 + param_15) - iVar6,param_16,param_9,param_10);
        bVar17 = 0xfffe < local_e;
        local_e = local_e + 1;
        bVar4 = SCARRY2(local_c,(uint)bVar17);
        local_c = local_c + (uint)bVar17;
        if ((bVar4) || (iVar12 < local_c)) break;
      } while ((local_c < iVar12) || (local_e <= iVar1 - 1U));
    }
    *param_8 = 2;
    *param_6 = 2;
    *param_5 = *param_1;
    puVar13[1] = param_1[1];
    puVar13[2] = param_1[2];
    puVar13[3] = param_1[3];
    uVar16 = *(undefined2 *)0x32a6;
    *(undefined2 *)0x0 = 0x6666;
    *(undefined2 *)0x2 = 0;
  }
  return;
}

