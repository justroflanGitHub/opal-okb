
void __cdecl16near FUN_144d_0ad4(void)

{
  byte bVar1;
  char cVar2;
  uint in_AX;
  undefined2 unaff_DS;
  
  bVar1 = (byte)in_AX;
  *(byte *)0x3b8 = bVar1;
  cVar2 = (char)(in_AX >> 8);
  if (cVar2 != '\0') goto LAB_144d_0af9;
  if (*(byte *)0x3b5 < 3) {
LAB_144d_0aef:
    if (0x13 < bVar1) {
LAB_144d_0af3:
      in_AX = 0x13;
    }
  }
  else {
    if (0x21 < bVar1) goto LAB_144d_0af3;
    if (bVar1 < 0x20) goto LAB_144d_0aef;
    in_AX = 5;
  }
  cVar2 = *(char *)(ulong)((in_AX & 0xff) + 0x410);
LAB_144d_0af9:
  *(int *)0x3ad = (int)cVar2;
  return;
}

