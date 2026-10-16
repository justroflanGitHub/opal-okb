
undefined2 __cdecl16far FUN_144d_128e(int *param_1)

{
  int iVar1;
  int iVar2;
  int *piVar3;
  undefined2 uVar4;
  undefined2 uVar5;
  undefined2 unaff_DS;
  
  uVar4 = 0;
  uVar5 = (undefined2)((ulong)param_1 >> 0x10);
  piVar3 = (int *)param_1;
  if (((*(byte *)(piVar3 + 5) & 3) == 2) &&
     (((*(byte *)(piVar3 + 5) & 8) != 0 ||
      ((*(byte *)(((int)(piVar3 + -0x212) / 0xc) * 6 + 0x514) & 1) != 0)))) {
    iVar1 = *param_1 - piVar3[3];
    if (0 < iVar1) {
      iVar2 = FUN_144d_148e(0x144d,*(undefined1 *)((int)piVar3 + 0xb),piVar3[3],piVar3[4],iVar1);
      if (iVar2 != iVar1) {
        *(byte *)(piVar3 + 5) = *(byte *)(piVar3 + 5) | 0x20;
        uVar4 = 0xffff;
      }
    }
  }
  iVar1 = piVar3[4];
  *param_1 = piVar3[3];
  piVar3[1] = iVar1;
  piVar3[2] = 0;
  return uVar4;
}

