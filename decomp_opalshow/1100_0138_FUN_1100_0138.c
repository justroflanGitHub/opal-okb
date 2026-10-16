
void __cdecl16far FUN_1100_0138(undefined2 param_1)

{
  undefined2 in_BX;
  undefined1 uVar1;
  undefined2 unaff_DS;
  
  uVar1 = (undefined1)((uint)in_BX >> 8);
  FUN_1100_0762();
  if (((char)((uint)param_1 >> 8) == '\0') && ((byte)param_1 <= *(byte *)0x2e6)) {
    (*(code *)*(undefined2 *)0x2f3)(CONCAT11(uVar1,*(undefined1 *)0x2d5));
  }
  FUN_1100_077e();
  return;
}

