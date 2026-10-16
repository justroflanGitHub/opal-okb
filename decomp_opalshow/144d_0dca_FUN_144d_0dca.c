
uint __cdecl16far FUN_144d_0dca(int *param_1)

{
  byte *pbVar1;
  int iVar2;
  byte *pbVar3;
  byte bVar4;
  int iVar5;
  undefined2 uVar6;
  undefined2 unaff_DS;
  
  iVar5 = ((int)((int *)param_1 + -0x212) / 0xc) * 6;
  uVar6 = (undefined2)((ulong)param_1 >> 0x10);
  if (((*(byte *)((int *)param_1 + 5) & 0x83) != 0) && ((*(byte *)((int *)param_1 + 5) & 0x40) == 0)
     ) {
    if ((*(byte *)((int *)param_1 + 5) & 2) == 0) {
      *(byte *)((int *)param_1 + 5) = *(byte *)((int *)param_1 + 5) | 1;
      pbVar1 = (byte *)(iVar5 + 0x514);
      *pbVar1 = *pbVar1 & 0xfb;
      if (((*(byte *)((int *)param_1 + 5) & 0xc) == 0) &&
         ((*(byte *)(((int)((int *)param_1 + -0x212) / 0xc) * 6 + 0x514) & 1) == 0)) {
        FUN_144d_1200((int *)param_1,uVar6);
      }
      else {
        iVar2 = ((int *)param_1)[4];
        *param_1 = ((int *)param_1)[3];
        ((int *)param_1)[1] = iVar2;
      }
      iVar5 = FUN_144d_1398(0x144d,*(undefined1 *)((int)(int *)param_1 + 0xb),((int *)param_1)[3],
                            ((int *)param_1)[4],*(undefined2 *)(iVar5 + 0x516));
      ((int *)param_1)[2] = iVar5;
      if ((iVar5 != 0) && (iVar5 != -1)) {
        ((int *)param_1)[2] = ((int *)param_1)[2] + -1;
        pbVar3 = (byte *)*param_1;
        *param_1 = *param_1 + 1;
        return (uint)*pbVar3;
      }
      if (((int *)param_1)[2] == 0) {
        bVar4 = 0x10;
      }
      else {
        bVar4 = 0x20;
      }
      *(byte *)((int *)param_1 + 5) = *(byte *)((int *)param_1 + 5) | bVar4;
      ((int *)param_1)[2] = 0;
    }
    else {
      *(byte *)((int *)param_1 + 5) = *(byte *)((int *)param_1 + 5) | 0x20;
    }
  }
  return 0xffff;
}

