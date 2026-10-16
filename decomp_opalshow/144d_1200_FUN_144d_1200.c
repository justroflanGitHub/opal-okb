
void __cdecl16near FUN_144d_1200(undefined2 *param_1)

{
  undefined2 uVar1;
  int iVar2;
  int iVar3;
  int iVar4;
  undefined2 uVar5;
  undefined2 unaff_DS;
  
  *(int *)0x59c = *(int *)0x59c + 1;
  iVar4 = (int)((undefined2 *)param_1 + -0x212) % 0xc;
  iVar2 = ((int)((undefined2 *)param_1 + -0x212) / 0xc) * 6;
  iVar3 = FUN_144d_15fb(0x200);
  uVar5 = (undefined2)((ulong)param_1 >> 0x10);
  ((undefined2 *)param_1)[3] = iVar3;
  ((undefined2 *)param_1)[4] = iVar4;
  if (iVar4 == 0 && iVar3 == 0) {
    *(byte *)((undefined2 *)param_1 + 5) = *(byte *)((undefined2 *)param_1 + 5) | 4;
    ((undefined2 *)param_1)[3] = iVar2 + 0x515;
    ((undefined2 *)param_1)[4] = unaff_DS;
    *(undefined2 *)(iVar2 + 0x516) = 1;
  }
  else {
    *(byte *)((undefined2 *)param_1 + 5) = *(byte *)((undefined2 *)param_1 + 5) | 8;
    *(undefined2 *)(iVar2 + 0x516) = 0x200;
  }
  uVar1 = ((undefined2 *)param_1)[4];
  *param_1 = ((undefined2 *)param_1)[3];
  ((undefined2 *)param_1)[1] = uVar1;
  ((undefined2 *)param_1)[2] = 0;
  return;
}

