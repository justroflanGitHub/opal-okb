
undefined1 * __cdecl16far
FUN_4000_5136(undefined2 *param_1,undefined1 *param_2,undefined2 param_3,int param_4)

{
  undefined1 *puVar1;
  int iVar2;
  undefined1 *puVar3;
  int iVar4;
  undefined2 in_DX;
  undefined2 *puVar5;
  int *piVar6;
  undefined2 uVar7;
  undefined2 unaff_DS;
  undefined4 local_14;
  undefined4 local_e;
  undefined4 local_6;
  
  if (*(char *)0x1da8 == '\0') {
    uVar7 = (undefined2)((ulong)param_1 >> 0x10);
    puVar5 = (undefined2 *)param_1;
    piVar6 = (int *)FUN_4000_54d9(*param_1,puVar5[1],puVar5[2],puVar5[3]);
    local_e = (int *)CONCAT22(in_DX,piVar6);
    FUN_4000_6e32(param_2 + (*local_e == 0x2d),param_3,piVar6[1] + param_4,piVar6,in_DX);
  }
  else {
    local_e = (int *)CONCAT22(*(undefined2 *)0x6488,(int *)*(undefined2 *)0x6486);
    iVar4 = *local_e;
    if (param_4 == *(int *)0x1daa) {
      iVar2 = *(int *)0x1daa;
      local_14 = (undefined1 *)CONCAT22(param_3,param_2 + iVar2 + (uint)(iVar4 == 0x2d));
      *local_14 = 0x30;
      (param_2 + iVar2 + (uint)(iVar4 == 0x2d))[1] = 0;
    }
  }
  local_6 = (undefined1 *)CONCAT22(param_3,param_2);
  puVar3 = local_6;
  if (*local_e == 0x2d) {
    local_6 = (undefined1 *)CONCAT22(param_3,param_2 + 1);
    *puVar3 = 0x2d;
  }
  uVar7 = (undefined2)((ulong)local_e >> 0x10);
  piVar6 = (int *)local_e;
  if (piVar6[1] < 1) {
    FUN_4000_541e((undefined1 *)local_6,local_6._2_2_,1);
    puVar1 = (undefined1 *)local_6 + 1;
    *local_6 = 0x30;
  }
  else {
    puVar1 = (undefined1 *)local_6 + piVar6[1];
  }
  local_6 = (undefined1 *)CONCAT22(local_6._2_2_,puVar1);
  if (0 < param_4) {
    FUN_4000_541e(puVar1,local_6._2_2_,1);
    *local_6 = 0x2e;
    if (piVar6[1] < 0) {
      if (*(char *)0x1da8 == '\0') {
        iVar4 = -piVar6[1];
        if (-param_4 != piVar6[1] && param_4 <= iVar4) {
          iVar4 = param_4;
        }
      }
      else {
        iVar4 = -piVar6[1];
      }
      FUN_4000_541e(puVar1 + 1,local_6._2_2_,iVar4);
      FUN_4000_74d6(puVar1 + 1,local_6._2_2_,0x30,iVar4);
    }
  }
  return param_2;
}

