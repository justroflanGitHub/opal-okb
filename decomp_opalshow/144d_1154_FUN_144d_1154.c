
void __cdecl16far FUN_144d_1154(int param_1,undefined2 *param_2)

{
  int iVar1;
  int iVar2;
  undefined2 uVar3;
  undefined2 unaff_DS;
  byte *local_6;
  
  iVar2 = ((int)((undefined2 *)param_2 + -0x212) / 0xc) * 6;
  _local_6 = (byte *)CONCAT22(unaff_DS,(byte *)(iVar2 + 0x514));
  uVar3 = (undefined2)((ulong)param_2 >> 0x10);
  if (param_1 == 0) {
    if ((*_local_6 & 0x10) != 0) {
      iVar2 = FUN_144d_16c0(*(undefined1 *)((int)(undefined2 *)param_2 + 0xb));
      if (iVar2 != 0) {
        FUN_144d_128e((undefined2 *)param_2,uVar3);
      }
    }
  }
  else if ((*_local_6 & 0x10) != 0) {
    iVar1 = FUN_144d_16c0(*(undefined1 *)((int)(undefined2 *)param_2 + 0xb));
    if (iVar1 != 0) {
      FUN_144d_128e((undefined2 *)param_2,uVar3);
      *_local_6 = 0;
      *(undefined2 *)(iVar2 + 0x516) = 0;
      *param_2 = 0;
      ((undefined2 *)param_2)[1] = 0;
      ((undefined2 *)param_2)[3] = 0;
      ((undefined2 *)param_2)[4] = 0;
    }
  }
  return;
}

