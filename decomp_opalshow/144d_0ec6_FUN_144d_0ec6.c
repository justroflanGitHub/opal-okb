
uint __cdecl16far FUN_144d_0ec6(byte param_1,int *param_2)

{
  uint uVar1;
  int *piVar2;
  int *piVar3;
  int iVar4;
  int iVar5;
  undefined2 uVar6;
  undefined2 unaff_DS;
  int local_6;
  
  iVar5 = (int)((ulong)param_2 >> 0x10);
  piVar2 = (int *)param_2;
  uVar1 = (uint)*(byte *)((int)piVar2 + 0xb);
  if (((*(byte *)(piVar2 + 5) & 0x83) != 0) && ((*(byte *)(piVar2 + 5) & 0x40) == 0)) {
    if ((*(byte *)(piVar2 + 5) & 1) != 0) {
      *(byte *)(piVar2 + 5) = *(byte *)(piVar2 + 5) | 0x20;
      piVar2[2] = 0;
      return 0xffff;
    }
    *(byte *)(piVar2 + 5) = *(byte *)(piVar2 + 5) | 2;
    *(byte *)(piVar2 + 5) = *(byte *)(piVar2 + 5) & 0xef;
    piVar2[2] = 0;
    local_6 = 0;
    if ((((*(byte *)(piVar2 + 5) & 0xc) == 0) &&
        ((*(byte *)(((int)(piVar2 + -0x212) / 0xc) * 6 + 0x514) & 1) == 0)) &&
       (((((piVar2 != (int *)0x430 || (iVar5 != 0x188e)) &&
          ((piVar2 != (int *)0x43c || (iVar5 != 0x188e)))) &&
         ((piVar2 != (int *)0x454 || (iVar5 != 0x188e)))) ||
        (iVar5 = FUN_144d_16c0(uVar1), iVar5 == 0)))) {
      FUN_144d_1200((int *)param_2,param_2._2_2_);
    }
    uVar6 = (undefined2)((ulong)param_2 >> 0x10);
    piVar3 = (int *)param_2;
    if (((*(byte *)(piVar3 + 5) & 8) == 0) &&
       ((*(byte *)(((int)(piVar3 + -0x212) / 0xc) * 6 + 0x514) & 1) == 0)) {
      iVar4 = 1;
      local_6 = FUN_144d_148e(0x144d,uVar1,&param_1);
    }
    else {
      iVar4 = *param_2 - piVar3[3];
      iVar5 = piVar3[4];
      *param_2 = piVar3[3] + 1;
      piVar3[1] = iVar5;
      piVar3[2] = *(int *)(((int)(piVar2 + -0x212) / 0xc) * 6 + 0x516) + -1;
      if (iVar4 < 1) {
        if ((*(byte *)(uVar1 + 0x3bc) & 0x20) != 0) {
          FUN_144d_131e(0x144d,uVar1,0,0,2);
        }
      }
      else {
        local_6 = FUN_144d_148e(0x144d,uVar1,piVar3[3],iVar5,iVar4);
      }
      **(byte **)((int *)param_2 + 3) = param_1;
    }
    if (local_6 == iVar4) {
      return (uint)param_1;
    }
  }
  *(byte *)((int *)param_2 + 5) = *(byte *)((int *)param_2 + 5) | 0x20;
  return 0xffff;
}

