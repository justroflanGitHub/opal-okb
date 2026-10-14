
void __stdcall16far FUN_3000_11c4(int *param_1,undefined2 *param_2,int *param_3)

{
  int iVar1;
  undefined2 uVar2;
  int iVar3;
  int *piVar4;
  int iVar5;
  int iVar6;
  undefined2 uVar7;
  undefined2 uVar8;
  undefined2 unaff_DS;
  undefined1 uVar9;
  char cVar10;
  char cVar11;
  bool bVar12;
  undefined4 local_18;
  undefined4 local_12;
  undefined4 local_e;
  
  uVar7 = ((undefined2 *)param_2)[1];
  *(undefined2 *)0x5de4 = *param_2;
  *(undefined2 *)0x5de6 = uVar7;
  FUN_3000_2225(0x1000);
  FUN_3000_2231(0x2e73);
  *param_1 = 1;
  ((int *)param_1)[1] = 0;
  if ((*param_3 != 1) || (((int *)param_3)[1] != 0)) {
    iVar1 = *param_3;
    *(undefined2 *)0x5dda = 1;
    if (0 < iVar1) {
      local_18 = param_1;
      iVar6 = *(int *)0x5dda;
      do {
        uVar7 = *(undefined2 *)0x5de2;
        *(undefined2 *)0x5ddc = *(undefined2 *)0x5de0;
        *(undefined2 *)0x5dde = uVar7;
        uVar7 = *(undefined2 *)0x5de6;
        *(undefined2 *)0x5de0 = *(undefined2 *)0x5de4;
        *(undefined2 *)0x5de2 = uVar7;
        uVar7 = (undefined2)((ulong)local_18 >> 0x10);
        piVar4 = (int *)local_18;
        *local_18 = iVar6;
        piVar4[1] = iVar6 >> 0xf;
        *(undefined2 *)0x5dd8 = 1;
        cVar11 = SBORROW2(iVar1,1);
        iVar3 = iVar1 + -1;
        uVar9 = iVar1 == 1;
        if (0 < iVar1) {
          local_e = param_2;
          local_12 = param_2;
          iVar5 = *(int *)0x5dd8;
          do {
            cVar10 = iVar3 < 0;
            func_0x00032294(0x2e73);
            FUN_3000_2225(0x2e73);
            FUN_3000_23cd(0x2e73);
            uVar8 = (undefined2)((ulong)local_e >> 0x10);
            if ((bool)uVar9 || cVar11 != cVar10) {
              func_0x00032294(0x2e73);
              FUN_3000_2225(0x2e73);
              FUN_3000_23cd(0x2e73);
              if (!(bool)uVar9 && cVar11 == cVar10) {
                *local_18 = iVar5;
                piVar4[1] = iVar5 >> 0xf;
                uVar2 = ((undefined2 *)local_e)[1];
                *(undefined2 *)0x5de0 = *local_e;
                *(undefined2 *)0x5de2 = uVar2;
              }
            }
            func_0x00032294(0x2e73);
            FUN_3000_2225(0x2e73);
            FUN_3000_23cd(0x2e73);
            if (!(bool)uVar9 && cVar11 == cVar10) {
              uVar2 = ((undefined2 *)local_12)[1];
              *(undefined2 *)0x5de4 = *local_12;
              *(undefined2 *)0x5de6 = uVar2;
            }
            local_e = (undefined2 *)CONCAT22(uVar8,(undefined2 *)local_e + 2);
            local_12 = (undefined2 *)CONCAT22(local_12._2_2_,(undefined2 *)local_12 + 2);
            bVar12 = SCARRY2(iVar5,1);
            iVar5 = iVar5 + 1;
            if (bVar12) break;
            cVar11 = SBORROW2(iVar1,iVar5);
            iVar3 = iVar1 - iVar5;
            uVar9 = iVar1 == iVar5;
          } while (iVar5 <= iVar1);
          *(int *)0x5dd8 = iVar5;
        }
        local_18 = (int *)CONCAT22(uVar7,piVar4 + 2);
        bVar12 = SCARRY2(iVar6,1);
        iVar6 = iVar6 + 1;
      } while ((!bVar12) && (iVar6 <= iVar1));
      *(int *)0x5dda = iVar6;
    }
  }
  return;
}

