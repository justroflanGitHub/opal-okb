
void __cdecl16near FUN_1100_0917(void)

{
  byte bVar1;
  undefined2 unaff_DS;
  
  bVar1 = *(byte *)0x1006;
  if (*(char *)0x2d6 == '\0') {
    bVar1 = bVar1 & 0xf | (*(byte *)0x1006 & 0x10) << 3 | (*(byte *)0x1002 & 7) << 4;
  }
  else if (*(char *)0x2fe == '\x02') {
    (*(code *)*(undefined2 *)0x318)();
    bVar1 = *(byte *)0x111f;
  }
  *(byte *)0x1007 = bVar1;
  return;
}

