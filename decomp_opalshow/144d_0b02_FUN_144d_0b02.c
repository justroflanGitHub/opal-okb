
undefined2 __cdecl16far FUN_144d_0b02(char *param_1,int param_2,int param_3,uint *param_4)

{
  uint *puVar1;
  char cVar2;
  char *pcVar3;
  uint uVar4;
  long lVar5;
  undefined2 uVar6;
  int iVar7;
  uint uVar8;
  uint *puVar9;
  undefined2 unaff_DS;
  bool bVar10;
  long lVar11;
  undefined4 local_1c;
  undefined4 local_18;
  undefined4 local_14;
  uint local_a;
  int local_8;
  
  lVar11 = FUN_144d_00c6(param_2,0,param_3,0);
  if ((param_2 == 0) || (param_3 == 0)) {
switchD_1000_6efd_caseD_74:
    uVar6 = 0;
  }
  else {
    uVar6 = (undefined2)((ulong)param_4 >> 0x10);
    puVar9 = (uint *)param_4;
    lVar5 = lVar11;
    if (((puVar9[5] & 0xc) == 0) &&
       (iVar7 = FUN_144d_16e4(puVar9,uVar6,0x424,unaff_DS),
       (*(byte *)((iVar7 / 0xc) * 6 + 0x514) & 1) == 0)) {
      puVar1 = puVar9 + 2;
      *puVar1 = *puVar1 - 1;
      if ((int)*puVar1 < 0) {
        FUN_144d_0ec6((int)*param_1,puVar9,uVar6);
      }
      else {
        cVar2 = *param_1;
        pcVar3 = (char *)*param_4;
        uVar4 = puVar9[1];
        uVar8 = *param_4;
        *param_4 = *param_4 + 1;
        if (uVar8 == 0xffff) {
          puVar9[1] = puVar9[1] + 0x1000;
        }
        *pcVar3 = cVar2;
      }
      if ((puVar9[5] & 0x20) != 0) goto switchD_1000_6efd_caseD_74;
      param_1 = (char *)CONCAT22(param_1._2_2_ +
                                 (-(uint)((char *)0xfffe < (char *)param_1) & 0x1000),
                                 (char *)param_1 + 1);
      lVar5 = CONCAT22((int)((ulong)lVar11 >> 0x10) - (uint)((int)lVar11 == 0),(int)lVar11 + -1);
    }
    if (((puVar9[5] & 8) == 0) &&
       (iVar7 = FUN_144d_16e4(puVar9,uVar6,0x424,unaff_DS),
       (*(byte *)((iVar7 / 0xc) * 6 + 0x514) & 1) == 0)) {
      if (lVar5 != 0) {
        local_1c = (uint *)CONCAT22(uVar6,puVar9 + 5);
        local_18 = (uint *)CONCAT22(uVar6,puVar9 + 2);
        do {
          local_8 = (int)((ulong)lVar5 >> 0x10);
          local_a = (uint)lVar5;
          *local_18 = *local_18 - 1;
          if ((int)*local_18 < 0) {
            FUN_144d_0ec6((int)*param_1,puVar9,uVar6);
          }
          else {
            cVar2 = *param_1;
            pcVar3 = (char *)*param_4;
            uVar4 = puVar9[1];
            uVar8 = *param_4;
            *param_4 = *param_4 + 1;
            if (uVar8 == 0xffff) {
              puVar9[1] = puVar9[1] + 0x1000;
            }
            *pcVar3 = cVar2;
          }
          if ((*local_1c & 0x20) != 0) break;
          param_1 = (char *)CONCAT22(param_1._2_2_ +
                                     (-(uint)((char *)0xfffe < (char *)param_1) & 0x1000),
                                     (char *)param_1 + 1);
          local_8 = local_8 - (uint)(local_a == 0);
          lVar5 = CONCAT22(local_8,local_a + -1);
        } while (local_a + -1 != 0 || local_8 != 0);
      }
    }
    else if (lVar5 != 0) {
      local_14 = (uint *)CONCAT22(uVar6,puVar9 + 5);
      local_18 = (uint *)CONCAT22(uVar6,puVar9 + 2);
      local_1c = (uint *)CONCAT22(uVar6,puVar9 + 2);
      do {
        local_8 = (int)((ulong)lVar5 >> 0x10);
        local_a = (uint)lVar5;
        if (*local_1c == 0) {
          *local_18 = *local_18 - 1;
          if ((int)*local_18 < 0) {
            FUN_144d_0ec6((int)*param_1,puVar9,uVar6);
          }
          else {
            cVar2 = *param_1;
            pcVar3 = (char *)*param_4;
            uVar4 = puVar9[1];
            uVar8 = *param_4;
            *param_4 = *param_4 + 1;
            if (uVar8 == 0xffff) {
              puVar9[1] = puVar9[1] + 0x1000;
            }
            *pcVar3 = cVar2;
          }
          if ((*local_14 & 0x20) != 0) break;
          param_1 = (char *)CONCAT22(param_1._2_2_ +
                                     (-(uint)((char *)0xfffe < (char *)param_1) & 0x1000),
                                     (char *)param_1 + 1);
          bVar10 = local_a == 0;
          local_a = local_a - 1;
        }
        else {
          if ((local_8 != 0) || (uVar8 = local_a, *local_1c <= local_a)) {
            uVar8 = puVar9[2];
          }
          FUN_144d_1712(*param_4,puVar9[1],(char *)param_1,param_1._2_2_,uVar8);
          uVar4 = *param_4;
          *param_4 = *param_4 + uVar8;
          puVar9[1] = puVar9[1] + (uint)CARRY2(uVar4,uVar8) * 0x1000;
          param_1 = (char *)CONCAT22(param_1._2_2_ +
                                     (uint)CARRY2((uint)(char *)param_1,uVar8) * 0x1000,
                                     (char *)param_1 + uVar8);
          bVar10 = local_a < uVar8;
          local_a = local_a - uVar8;
          *local_1c = *local_1c - uVar8;
        }
        local_8 = local_8 - (uint)bVar10;
        lVar5 = CONCAT22(local_8,local_a);
      } while (local_a != 0 || local_8 != 0);
    }
    uVar6 = FUN_144d_00fa(lVar11 - lVar5,param_2,0);
  }
  return uVar6;
}

