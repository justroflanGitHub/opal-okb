
undefined2 __cdecl16far FUN_144d_090a(undefined2 param_1,undefined2 param_2)

{
  int *piVar1;
  undefined1 *puVar2;
  int iVar3;
  undefined2 uVar4;
  int iVar5;
  undefined2 unaff_DS;
  undefined2 local_c;
  
  _local_c = (int *)CONCAT22(unaff_DS,(int *)0x430);
  iVar3 = FUN_144d_079e(param_1,param_2);
  uVar4 = FUN_144d_105c(0x430,unaff_DS);
  iVar5 = FUN_144d_0b02(param_1,param_2,1,iVar3,0x430,unaff_DS);
  FUN_144d_1154(uVar4,0x430,unaff_DS);
  if (iVar5 == iVar3) {
    piVar1 = (int *)0x434;
    *piVar1 = *piVar1 + -1;
    if (*piVar1 < 0) {
      FUN_144d_0ec6(10,0x430,unaff_DS);
    }
    else {
      puVar2 = (undefined1 *)*_local_c;
      *_local_c = *_local_c + 1;
      *puVar2 = 10;
    }
    uVar4 = 0;
  }
  else {
    uVar4 = 0xffff;
  }
  return uVar4;
}

