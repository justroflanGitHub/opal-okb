
undefined1 * __cdecl16far FUN_144d_088c(undefined1 *param_1,int param_2)

{
  int *piVar1;
  byte *pbVar2;
  uint uVar3;
  undefined2 unaff_DS;
  undefined4 local_6;
  
  local_6 = (undefined1 *)CONCAT22(param_2,param_1);
  while( true ) {
    piVar1 = (int *)0x428;
    *piVar1 = *piVar1 + -1;
    if (*piVar1 < 0) {
      uVar3 = FUN_144d_0dca(0x424);
    }
    else {
      pbVar2 = (byte *)*(undefined2 *)0x424;
      *(int *)0x424 = *(int *)0x424 + 1;
      uVar3 = (uint)*pbVar2;
    }
    if (uVar3 == 10) goto LAB_144d_08e6;
    if (uVar3 == 0xffff) break;
    *local_6 = (char)uVar3;
    local_6 = (undefined1 *)CONCAT22(local_6._2_2_,(undefined1 *)local_6 + 1);
  }
  if (((undefined1 *)local_6 == param_1) && (local_6._2_2_ == param_2)) {
    param_1 = (undefined1 *)0x0;
  }
  else {
LAB_144d_08e6:
    *local_6 = 0;
  }
  return param_1;
}

