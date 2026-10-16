
void __cdecl16near FUN_1100_0f90(void)

{
  byte bVar1;
  long lVar2;
  undefined2 uVar3;
  undefined2 unaff_SS;
  
  bVar1 = *(byte *)0x2d4;
  lVar2 = (ulong)bVar1 * (ulong)(uint)(*(int *)0x2e4 << 4);
  uVar3 = (undefined2)((ulong)lVar2 >> 0x10);
  *(undefined2 *)0x44e = (int)lVar2;
  *(byte *)0x462 = bVar1;
  return;
}

