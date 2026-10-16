
undefined2 __cdecl16far FUN_144d_105c(undefined2 *param_1)

{
  undefined2 uVar1;
  undefined2 uVar2;
  int iVar3;
  int iVar4;
  int iVar5;
  undefined2 unaff_DS;
  int local_4;
  
  *(int *)0x59c = *(int *)0x59c + 1;
  if (((undefined2 *)param_1 == (undefined2 *)0x430) && (param_1._2_2_ == 0x188e)) {
    local_4 = 0;
  }
  else if (((undefined2 *)param_1 == (undefined2 *)0x43c) && (param_1._2_2_ == 0x188e)) {
    local_4 = 1;
  }
  else {
    if ((undefined2 *)param_1 != (undefined2 *)0x454) {
      return 0;
    }
    if (param_1._2_2_ != 0x188e) {
      return 0;
    }
    local_4 = 2;
  }
  if (((*(byte *)((undefined2 *)param_1 + 5) & 0xc) == 0) &&
     (iVar4 = (int)((undefined2 *)param_1 + -0x212) % 0xc,
     (*(byte *)(((int)((undefined2 *)param_1 + -0x212) / 0xc) * 6 + 0x514) & 1) == 0)) {
    iVar5 = local_4 * 4;
    if (*(int *)(iVar5 + 0x590) == 0 && *(int *)(iVar5 + 0x592) == 0) {
      iVar3 = FUN_144d_15fb(0x200);
      *(int *)(iVar5 + 0x590) = iVar3;
      *(int *)(iVar5 + 0x592) = iVar4;
      if (iVar4 == 0 && iVar3 == 0) {
        return 0;
      }
    }
    iVar4 = ((int)((undefined2 *)param_1 + -0x212) / 0xc) * 6;
    uVar1 = *(undefined2 *)(local_4 * 4 + 0x590);
    uVar2 = *(undefined2 *)(local_4 * 4 + 0x592);
    ((undefined2 *)param_1)[3] = uVar1;
    ((undefined2 *)param_1)[4] = uVar2;
    *param_1 = uVar1;
    ((undefined2 *)param_1)[1] = uVar2;
    *(undefined2 *)(iVar4 + 0x516) = 0x200;
    ((undefined2 *)param_1)[2] = 0x200;
    *(undefined1 *)(iVar4 + 0x514) = 0x11;
    *(byte *)((undefined2 *)param_1 + 5) = *(byte *)((undefined2 *)param_1 + 5) | 2;
    return 1;
  }
  return 0;
}

