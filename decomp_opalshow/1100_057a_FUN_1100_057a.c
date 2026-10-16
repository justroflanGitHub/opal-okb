
/* WARNING: Instruction at (ram,0x0001159c) overlaps instruction at (ram,0x0001159b)
    */

void __cdecl16far FUN_1100_057a(undefined2 param_1)

{
  byte bVar1;
  undefined1 uVar2;
  undefined2 unaff_DS;
  byte in_ZF;
  
  FUN_1100_0762();
  bVar1 = *(byte *)0x2c8;
  uVar2 = 0;
  if ((char)param_1 != '\0' || (char)((uint)param_1 >> 8) != '\0') {
    uVar2 = 0xff;
  }
  *(undefined1 *)0x2c8 = uVar2;
  if ((in_ZF & 1) == 0) {
    bVar1 = bVar1 >> 1;
  }
  FUN_1100_0677(bVar1);
  FUN_1100_077e();
  return;
}

